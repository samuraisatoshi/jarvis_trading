#!/usr/bin/env python3
"""
Trading Config Manager - Efficient YAML configuration manipulation for JARVIS Trading.

Adapted from genSyntheticCroped config-manager skill.
Provides atomic operations on trading_config.yaml without loading entire file into context.
Token-efficient config management optimized for trading bot operations.

Usage:
    # Get specific value
    python trading_config_manager.py get order_cooldown.min_price_gap_percent

    # Set specific value
    python trading_config_manager.py set order_cooldown.min_price_gap_percent 3.0

    # Update multiple values at once
    python trading_config_manager.py batch-set --json '{"position_management.max_concurrent_positions": 3, "cash_management.min_cash_reserve": 0.25}'

    # Validate configuration
    python trading_config_manager.py validate
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap
except ImportError:
    print(json.dumps({
        "error": "ruamel.yaml not installed. Install with: pip install ruamel.yaml",
        "success": False
    }))
    sys.exit(1)


class TradingConfigManager:
    """Manages YAML trading configuration with atomic operations."""

    def __init__(self, config_path: str = "config/trading_config.yaml"):
        """
        Initialize trading config manager.

        Args:
            config_path: Path to trading_config.yaml relative to project root
        """
        script_path = Path(__file__).resolve()
        self.project_root = script_path.parent.parent
        self.config_path = self.project_root / config_path

        # Initialize YAML handler with proper settings
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=2, offset=0)

        # Track modifications for audit
        self.modifications = []

    def _load_config(self) -> CommentedMap:
        """Load config file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return self.yaml.load(f)

    def _save_config(self, config: CommentedMap) -> None:
        """Save config file preserving comments and formatting."""
        # Create backup before saving
        backup_path = self.config_path.with_suffix('.yaml.bak')
        if self.config_path.exists():
            import shutil
            shutil.copy2(self.config_path, backup_path)

        with open(self.config_path, 'w', encoding='utf-8') as f:
            self.yaml.dump(config, f)

    def _get_nested_value(self, config: Dict, key_path: str) -> Any:
        """Get value from nested dict using dot notation."""
        keys = key_path.split('.')
        value = config

        for key in keys:
            if not isinstance(value, dict):
                raise KeyError(f"Cannot navigate through non-dict at key '{key}'")
            if key not in value:
                raise KeyError(f"Key '{key}' not found in path '{key_path}'")
            value = value[key]

        return value

    def _set_nested_value(self, config: CommentedMap, key_path: str, value: Any) -> None:
        """Set value in nested dict using dot notation."""
        keys = key_path.split('.')
        current = config

        # Navigate to parent
        for key in keys[:-1]:
            if key not in current:
                raise KeyError(f"Parent key '{key}' not found in path '{key_path}'")
            current = current[key]

        # Set value
        final_key = keys[-1]
        if final_key not in current:
            raise KeyError(f"Key '{final_key}' not found. Use 'add' command to create new keys.")

        current[final_key] = value

    def get(self, key_path: str) -> Dict[str, Any]:
        """Get specific configuration value."""
        try:
            config = self._load_config()
            value = self._get_nested_value(config, key_path)

            return {
                "success": True,
                "key": key_path,
                "value": value,
                "type": type(value).__name__
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "key": key_path
            }

    def set(self, key_path: str, value: Any) -> Dict[str, Any]:
        """Set specific configuration value with type conversion."""
        try:
            config = self._load_config()

            # Get current value to determine type
            current_value = self._get_nested_value(config, key_path)

            # Type conversion
            if isinstance(current_value, bool):
                if isinstance(value, str):
                    value = value.lower() in ('true', 'yes', '1', 'on')
                else:
                    value = bool(value)
            elif isinstance(current_value, int):
                value = int(value)
            elif isinstance(current_value, float):
                value = float(value)
            elif isinstance(current_value, list):
                if isinstance(value, str) and ',' in value:
                    value = [v.strip() for v in value.split(',')]
                elif not isinstance(value, list):
                    value = [value]

            # Set value
            old_value = current_value
            self._set_nested_value(config, key_path, value)
            self._save_config(config)

            # Track modification
            self.modifications.append({
                "timestamp": datetime.now().isoformat(),
                "key": key_path,
                "old_value": old_value,
                "new_value": value
            })

            return {
                "success": True,
                "key": key_path,
                "old_value": old_value,
                "new_value": value,
                "message": f"Updated {key_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "key": key_path
            }

    def batch_set(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Set multiple configuration values in a single transaction."""
        try:
            config = self._load_config()
            results = []
            errors = []

            for key_path, value in updates.items():
                try:
                    # Get current value to determine type
                    current_value = self._get_nested_value(config, key_path)

                    # Type conversion
                    if isinstance(current_value, bool):
                        if isinstance(value, str):
                            value = value.lower() in ('true', 'yes', '1', 'on')
                        else:
                            value = bool(value)
                    elif isinstance(current_value, int):
                        value = int(value)
                    elif isinstance(current_value, float):
                        value = float(value)
                    elif isinstance(current_value, list):
                        if isinstance(value, str) and ',' in value:
                            value = [v.strip() for v in value.split(',')]
                        elif not isinstance(value, list):
                            value = [value]

                    # Set value
                    old_value = current_value
                    self._set_nested_value(config, key_path, value)

                    results.append({
                        "key": key_path,
                        "old_value": old_value,
                        "new_value": value,
                        "success": True
                    })

                    # Track modification
                    self.modifications.append({
                        "timestamp": datetime.now().isoformat(),
                        "key": key_path,
                        "old_value": old_value,
                        "new_value": value
                    })
                except Exception as e:
                    errors.append({
                        "key": key_path,
                        "error": str(e),
                        "success": False
                    })

            # Save config once with all changes
            if results:
                self._save_config(config)

            return {
                "success": len(errors) == 0,
                "updated": len(results),
                "failed": len(errors),
                "results": results,
                "errors": errors if errors else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def validate_trading_config(self) -> Dict[str, Any]:
        """Validate trading configuration with domain-specific rules."""
        try:
            config = self._load_config()
            warnings = []
            errors = []

            # Check position sizes sum
            if 'position_management' in config:
                position_sizes = config['position_management'].get('position_sizes', {})
                total = sum(position_sizes.values())
                if total > 1.0:
                    errors.append(f"Position sizes sum to {total:.2%}, exceeding 100%")

            # Check cash reserve
            min_reserve = self._get_nested_value(config, 'cash_management.min_cash_reserve')
            if min_reserve < 0.1:
                warnings.append(f"Cash reserve {min_reserve:.1%} is very low, consider >= 10%")

            # Check cool down settings
            min_gap = self._get_nested_value(config, 'order_cooldown.min_price_gap_percent')
            if min_gap < 1.0:
                warnings.append(f"Price gap {min_gap}% might be too small for sideways markets")

            # Check risk settings
            max_drawdown = self._get_nested_value(config, 'risk_management.max_drawdown_percent')
            daily_loss = self._get_nested_value(config, 'risk_management.daily_loss_limit_percent')

            if daily_loss > max_drawdown:
                errors.append(f"Daily loss limit {daily_loss}% exceeds max drawdown {max_drawdown}%")

            # Check required sections
            required_sections = [
                'trading',
                'position_management',
                'order_cooldown',
                'cash_management',
                'risk_management'
            ]

            missing_sections = []
            for section in required_sections:
                if section not in config:
                    missing_sections.append(section)

            is_valid = len(errors) == 0 and len(missing_sections) == 0

            return {
                "success": True,
                "valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "missing_sections": missing_sections,
                "config_path": str(self.config_path)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_audit_trail(self) -> Dict[str, Any]:
        """Get audit trail of all modifications in this session."""
        return {
            "success": True,
            "modifications": self.modifications,
            "count": len(self.modifications)
        }

    def apply_preset(self, preset: str) -> Dict[str, Any]:
        """Apply a preset configuration profile."""
        presets = {
            "conservative": {
                "position_management.max_concurrent_positions": 3,
                "position_management.max_asset_exposure": 0.20,
                "cash_management.min_cash_reserve": 0.30,
                "order_cooldown.min_price_gap_percent": 3.0,
                "risk_management.max_drawdown_percent": 10.0,
                "risk_management.daily_loss_limit_percent": 3.0
            },
            "moderate": {
                "position_management.max_concurrent_positions": 5,
                "position_management.max_asset_exposure": 0.25,
                "cash_management.min_cash_reserve": 0.20,
                "order_cooldown.min_price_gap_percent": 2.0,
                "risk_management.max_drawdown_percent": 15.0,
                "risk_management.daily_loss_limit_percent": 5.0
            },
            "aggressive": {
                "position_management.max_concurrent_positions": 8,
                "position_management.max_asset_exposure": 0.35,
                "cash_management.min_cash_reserve": 0.10,
                "order_cooldown.min_price_gap_percent": 1.0,
                "risk_management.max_drawdown_percent": 20.0,
                "risk_management.daily_loss_limit_percent": 7.0
            },
            "scalping": {
                "position_management.position_sizes.1h": 0.03,
                "position_management.position_sizes.4h": 0.05,
                "order_cooldown.cooldown_periods.1h": 900,
                "order_cooldown.min_price_gap_percent": 0.5,
                "cash_management.min_cash_reserve": 0.40
            }
        }

        if preset not in presets:
            return {
                "success": False,
                "error": f"Unknown preset '{preset}'. Available: {', '.join(presets.keys())}"
            }

        return self.batch_set(presets[preset])


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Trading configuration manager for JARVIS Trading",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get value
  python trading_config_manager.py get order_cooldown.min_price_gap_percent

  # Set value
  python trading_config_manager.py set order_cooldown.min_price_gap_percent 3.0

  # Apply preset
  python trading_config_manager.py preset conservative

  # Validate config
  python trading_config_manager.py validate

  # Batch update
  python trading_config_manager.py batch-set --json '{"cash_management.min_cash_reserve": 0.25}'

  # Get audit trail
  python trading_config_manager.py audit
        """
    )

    parser.add_argument(
        'command',
        choices=['get', 'set', 'batch-set', 'validate', 'preset', 'audit', 'list', 'get-section'],
        help='Command to execute'
    )

    parser.add_argument(
        'key',
        nargs='?',
        help='Key path (dot notation) or preset name'
    )

    parser.add_argument(
        'value',
        nargs='?',
        help='Value to set'
    )

    parser.add_argument(
        '--json',
        dest='json_data',
        help='JSON string with updates for batch-set'
    )

    parser.add_argument(
        '--config',
        default='config/trading_config.yaml',
        help='Path to config file (default: config/trading_config.yaml)'
    )

    args = parser.parse_args()

    manager = TradingConfigManager(args.config)

    # Execute command
    if args.command == 'get':
        if not args.key:
            print(json.dumps({"error": "Key path required for get command", "success": False}))
            sys.exit(1)
        result = manager.get(args.key)

    elif args.command == 'set':
        if not args.key or args.value is None:
            print(json.dumps({"error": "Key path and value required for set command", "success": False}))
            sys.exit(1)
        result = manager.set(args.key, args.value)

    elif args.command == 'batch-set':
        if not args.json_data:
            print(json.dumps({"error": "--json required for batch-set command", "success": False}))
            sys.exit(1)
        try:
            updates = json.loads(args.json_data)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON: {str(e)}", "success": False}))
            sys.exit(1)
        result = manager.batch_set(updates)

    elif args.command == 'validate':
        result = manager.validate_trading_config()

    elif args.command == 'preset':
        if not args.key:
            print(json.dumps({"error": "Preset name required", "success": False}))
            sys.exit(1)
        result = manager.apply_preset(args.key)

    elif args.command == 'audit':
        result = manager.get_audit_trail()

    elif args.command == 'get-section':
        if not args.key:
            print(json.dumps({"error": "Section name required", "success": False}))
            sys.exit(1)
        result = manager.get(args.key)

    # Output JSON result
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    # Exit with appropriate code
    sys.exit(0 if result.get('success', False) else 1)


if __name__ == '__main__':
    main()