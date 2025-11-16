"""
Telegram Notifier for Trading Alerts

Sends formatted trading notifications to Telegram bot.
Supports markdown/HTML formatting, rate limiting, and retry logic.

Features:
- Rich message formatting (markdown/HTML)
- Rate limiting (max 30 messages/minute)
- Automatic retry on failures (3 attempts)
- Image/chart sending
- Whitelist security (authorized chat_ids)
- Comprehensive error handling
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
import logging

import requests
from loguru import logger


@dataclass
class RateLimiter:
    """Rate limiter to prevent Telegram API spam."""

    max_messages: int = 30  # Max messages per window
    time_window: int = 60  # Time window in seconds
    messages_sent: List[float] = field(default_factory=list)

    def can_send(self) -> bool:
        """Check if we can send another message."""
        now = time.time()

        # Remove messages outside window
        self.messages_sent = [
            ts for ts in self.messages_sent if now - ts < self.time_window
        ]

        return len(self.messages_sent) < self.max_messages

    def record_message(self):
        """Record that a message was sent."""
        self.messages_sent.append(time.time())

    def wait_time(self) -> float:
        """Get wait time before next message can be sent."""
        if self.can_send():
            return 0.0

        now = time.time()
        oldest_message = min(self.messages_sent)
        return self.time_window - (now - oldest_message)


class TelegramNotifier:
    """
    Telegram notification service for trading alerts.

    Responsibilities:
    - Send formatted messages to Telegram
    - Handle rate limiting
    - Retry failed sends
    - Send charts and images
    - Validate authorized users
    """

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        authorized_chat_ids: Optional[List[str]] = None,
        max_retries: int = 3,
        parse_mode: str = "MarkdownV2",
    ):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Default chat ID to send messages to
            authorized_chat_ids: Whitelist of authorized chat IDs (security)
            max_retries: Maximum retry attempts on failures
            parse_mode: Message parse mode (Markdown, MarkdownV2, HTML)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.authorized_chat_ids = authorized_chat_ids or [chat_id]
        self.max_retries = max_retries
        self.parse_mode = parse_mode

        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.rate_limiter = RateLimiter()

        # Track statistics
        self.stats = {
            "messages_sent": 0,
            "messages_failed": 0,
            "rate_limited": 0,
            "last_message_time": None,
        }

        logger.info(
            f"Telegram Notifier initialized:\n"
            f"  Chat ID: {chat_id}\n"
            f"  Parse mode: {parse_mode}\n"
            f"  Max retries: {max_retries}\n"
            f"  Authorized chats: {len(self.authorized_chat_ids)}"
        )

    def _is_authorized(self, chat_id: str) -> bool:
        """Check if chat ID is authorized."""
        return chat_id in self.authorized_chat_ids

    def _escape_markdown(self, text: str) -> str:
        """
        Escape special characters for MarkdownV2.

        MarkdownV2 requires escaping: _ * [ ] ( ) ~ ` > # + - = | { } . !
        """
        if self.parse_mode != "MarkdownV2":
            return text

        special_chars = [
            "_",
            "*",
            "[",
            "]",
            "(",
            ")",
            "~",
            "`",
            ">",
            "#",
            "+",
            "-",
            "=",
            "|",
            "{",
            "}",
            ".",
            "!",
        ]

        for char in special_chars:
            text = text.replace(char, f"\\{char}")

        return text

    def _wait_for_rate_limit(self):
        """Wait if rate limit exceeded."""
        if not self.rate_limiter.can_send():
            wait_time = self.rate_limiter.wait_time()
            logger.warning(
                f"Rate limit reached. Waiting {wait_time:.1f}s before sending..."
            )
            self.stats["rate_limited"] += 1
            time.sleep(wait_time)

    def send_message(
        self,
        message: str,
        chat_id: Optional[str] = None,
        disable_notification: bool = False,
        disable_web_page_preview: bool = True,
    ) -> bool:
        """
        Send text message to Telegram.

        Args:
            message: Message text (markdown/HTML formatted)
            chat_id: Override default chat_id
            disable_notification: Silent notification
            disable_web_page_preview: Don't show link previews

        Returns:
            True if sent successfully, False otherwise
        """
        target_chat = chat_id or self.chat_id

        if not self._is_authorized(target_chat):
            logger.error(f"Unauthorized chat_id: {target_chat}")
            return False

        # Rate limiting
        self._wait_for_rate_limit()

        # Prepare payload
        payload = {
            "chat_id": target_chat,
            "text": message,
            "parse_mode": self.parse_mode,
            "disable_notification": disable_notification,
            "disable_web_page_preview": disable_web_page_preview,
        }

        # Retry logic
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/sendMessage", json=payload, timeout=10
                )
                response.raise_for_status()

                result = response.json()
                if result.get("ok"):
                    self.rate_limiter.record_message()
                    self.stats["messages_sent"] += 1
                    self.stats["last_message_time"] = datetime.utcnow().isoformat()
                    logger.debug(f"Message sent successfully to {target_chat}")
                    return True
                else:
                    logger.error(f"Telegram API error: {result}")

            except requests.exceptions.Timeout:
                logger.warning(
                    f"Timeout sending message (attempt {attempt + 1}/{self.max_retries})"
                )
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Request error (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
            except Exception as e:
                logger.error(f"Unexpected error sending message: {e}", exc_info=True)

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)

        # All retries failed
        self.stats["messages_failed"] += 1
        logger.error(f"Failed to send message after {self.max_retries} attempts")
        return False

    def send_image(
        self,
        image_path: Union[str, Path],
        caption: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> bool:
        """
        Send image to Telegram.

        Args:
            image_path: Path to image file
            caption: Image caption (optional)
            chat_id: Override default chat_id

        Returns:
            True if sent successfully, False otherwise
        """
        target_chat = chat_id or self.chat_id

        if not self._is_authorized(target_chat):
            logger.error(f"Unauthorized chat_id: {target_chat}")
            return False

        image_path = Path(image_path)
        if not image_path.exists():
            logger.error(f"Image not found: {image_path}")
            return False

        # Rate limiting
        self._wait_for_rate_limit()

        # Prepare payload
        files = {"photo": open(image_path, "rb")}
        data = {"chat_id": target_chat}

        if caption:
            data["caption"] = caption
            data["parse_mode"] = self.parse_mode

        # Retry logic
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/sendPhoto", data=data, files=files, timeout=30
                )
                response.raise_for_status()

                result = response.json()
                if result.get("ok"):
                    self.rate_limiter.record_message()
                    self.stats["messages_sent"] += 1
                    logger.debug(f"Image sent successfully to {target_chat}")
                    return True
                else:
                    logger.error(f"Telegram API error: {result}")

            except Exception as e:
                logger.error(
                    f"Error sending image (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

            # Wait before retry
            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)

        # All retries failed
        self.stats["messages_failed"] += 1
        logger.error(f"Failed to send image after {self.max_retries} attempts")
        return False

    def send_document(
        self,
        document_path: Union[str, Path],
        caption: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> bool:
        """
        Send document to Telegram.

        Args:
            document_path: Path to document file
            caption: Document caption (optional)
            chat_id: Override default chat_id

        Returns:
            True if sent successfully, False otherwise
        """
        target_chat = chat_id or self.chat_id

        if not self._is_authorized(target_chat):
            logger.error(f"Unauthorized chat_id: {target_chat}")
            return False

        document_path = Path(document_path)
        if not document_path.exists():
            logger.error(f"Document not found: {document_path}")
            return False

        # Rate limiting
        self._wait_for_rate_limit()

        # Prepare payload
        files = {"document": open(document_path, "rb")}
        data = {"chat_id": target_chat}

        if caption:
            data["caption"] = caption
            data["parse_mode"] = self.parse_mode

        # Retry logic
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/sendDocument", data=data, files=files, timeout=30
                )
                response.raise_for_status()

                result = response.json()
                if result.get("ok"):
                    self.rate_limiter.record_message()
                    self.stats["messages_sent"] += 1
                    logger.debug(f"Document sent successfully to {target_chat}")
                    return True
                else:
                    logger.error(f"Telegram API error: {result}")

            except Exception as e:
                logger.error(
                    f"Error sending document (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

            # Wait before retry
            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)

        # All retries failed
        self.stats["messages_failed"] += 1
        logger.error(f"Failed to send document after {self.max_retries} attempts")
        return False

    def get_stats(self) -> Dict:
        """Get notifier statistics."""
        return {
            **self.stats,
            "rate_limit_remaining": self.rate_limiter.max_messages
            - len(self.rate_limiter.messages_sent),
        }

    def test_connection(self) -> bool:
        """
        Test Telegram bot connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                bot_info = result.get("result", {})
                logger.info(
                    f"Telegram bot connected:\n"
                    f"  Username: @{bot_info.get('username')}\n"
                    f"  Name: {bot_info.get('first_name')}\n"
                    f"  ID: {bot_info.get('id')}"
                )
                return True
            else:
                logger.error(f"Bot connection failed: {result}")
                return False

        except Exception as e:
            logger.error(f"Error testing connection: {e}", exc_info=True)
            return False
