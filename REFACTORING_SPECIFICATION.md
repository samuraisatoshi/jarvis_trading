# Telegram Bot Refactoring Specification

## Current State Analysis

**File**: scripts/telegram_bot_hybrid.py
**Lines**: 899 (violates 500-line limit)
**Issues**:
- Single responsibility violation: Bot handles UI, trading logic, data access, formatting
- 251 hardcoded strings
- No dependency injection
- Tight coupling to Binance client and SQLite
- All handlers in one class

## Target Architecture (DDD + SOLID)

### Module Structure
```
src/infrastructure/telegram/
├── __init__.py
├── bot_manager.py              # < 300 lines - Bot orchestrator
├── handlers/
│   ├── __init__.py
│   ├── command_handlers.py     # < 300 lines - Command logic
│   ├── callback_handlers.py    # < 200 lines - Button callbacks
│   └── message_handlers.py     # < 200 lines - Text message handlers
└── formatters/
    ├── __init__.py
    └── message_formatter.py    # < 200 lines - Message formatting
```

### Config Structure
```
config/
├── bot_messages.yaml           # All user-facing strings
└── bot_settings.yaml           # Bot configuration parameters
```

## Refactoring Steps

### Step 1: Extract Strings to YAML (TODO #80)

**Action**: Use yaml-manager skill to extract all hardcoded strings from telegram_bot_hybrid.py

**Target**: config/bot_messages.yaml

**Categories**:
- commands.{command_name}.text
- commands.{command_name}.buttons
- errors.{error_type}
- feedback.{action}
- portfolio.{section}
- watchlist.{section}
- signals.{section}

**Token Savings**: 95%+ on future message modifications

### Step 2: Create Module Structure (TODO #81)

**Action**: Create directory structure in src/infrastructure/telegram/

**Files to create**:
1. `src/infrastructure/telegram/__init__.py`
2. `src/infrastructure/telegram/bot_manager.py`
3. `src/infrastructure/telegram/handlers/__init__.py`
4. `src/infrastructure/telegram/handlers/command_handlers.py`
5. `src/infrastructure/telegram/handlers/callback_handlers.py`
6. `src/infrastructure/telegram/handlers/message_handlers.py`
7. `src/infrastructure/telegram/formatters/__init__.py`
8. `src/infrastructure/telegram/formatters/message_formatter.py`

### Step 3: Extract Command Handlers (TODO #82)

**Source Methods** (from EnhancedTradingBot):
- `start()` - Menu principal
- `help()` - Lista comandos
- `status()` - Status sistema
- `portfolio()` - Portfolio info
- `watchlist()` - Watchlist
- `signals()` - Sinais ativos
- `buy_market()` - Executar compra
- `sell_market()` - Executar venda
- `candles()` - Gráficos
- `history()` - Histórico
- `add_symbol()` - Adicionar símbolo
- `remove_symbol()` - Remover símbolo
- `performance()` - Performance
- `handle_settings()` - Configurações

**Target**: `handlers/command_handlers.py`

**Design**:
```python
class CommandHandlers:
    def __init__(self, 
                 binance_client: BinanceRESTClient,
                 db_manager: DatabaseManager,
                 message_formatter: MessageFormatter,
                 config: dict):
        # Dependency injection
        self.binance_client = binance_client
        self.db = db_manager
        self.formatter = message_formatter
        self.config = config
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Menu principal."""
        ...
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista de comandos."""
        ...
    
    # ... demais handlers
```

### Step 4: Extract Callback Handlers (TODO #83)

**Source Methods**:
- `button_handler()` - Processa callbacks de botões inline

**Target**: `handlers/callback_handlers.py`

**Design**:
```python
class CallbackHandlers:
    def __init__(self, 
                 command_handlers: CommandHandlers,
                 message_formatter: MessageFormatter):
        self.commands = command_handlers
        self.formatter = message_formatter
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Router para callbacks."""
        query = update.callback_query
        await query.answer()
        
        callback_map = {
            'portfolio': self.commands.portfolio,
            'signals': self.commands.signals,
            'watchlist': self.commands.watchlist,
            # ... outros callbacks
        }
        
        handler = callback_map.get(query.data)
        if handler:
            await handler(update, context)
```

### Step 5: Extract Message Formatter (TODO #84)

**Responsibilities**:
- Formatar mensagens de portfolio
- Formatar mensagens de sinais
- Formatar mensagens de watchlist
- Formatar mensagens de erro
- Carregar templates do YAML

**Target**: `formatters/message_formatter.py`

**Design**:
```python
class MessageFormatter:
    def __init__(self, config_path: str = 'config/bot_messages.yaml'):
        self.messages = self._load_messages(config_path)
    
    def _load_messages(self, path: str) -> dict:
        """Load messages from YAML using yaml-manager pattern."""
        ...
    
    def format_portfolio(self, holdings: List[dict], total: float) -> str:
        """Format portfolio message."""
        ...
    
    def format_signals(self, signals: List[dict]) -> str:
        """Format signals message."""
        ...
    
    def format_error(self, error_type: str, **kwargs) -> str:
        """Format error message."""
        template = self.messages['errors'][error_type]
        return template.format(**kwargs)
```

### Step 6: Refactor Bot Manager (TODO #85)

**Target**: `bot_manager.py`

**Responsibilities**:
- Initialize bot application
- Register handlers
- Manage bot lifecycle
- Coordinate dependencies

**Design**:
```python
class TelegramBotManager:
    """Main bot orchestrator following SOLID principles."""
    
    def __init__(self, 
                 token: str,
                 binance_client: BinanceRESTClient,
                 db_path: str,
                 account_id: str):
        self.token = token
        self.binance_client = binance_client
        self.db_path = db_path
        self.account_id = account_id
        
        # Initialize components
        self.formatter = MessageFormatter()
        self.db_manager = DatabaseManager(db_path)
        self.command_handlers = CommandHandlers(
            binance_client=binance_client,
            db_manager=self.db_manager,
            message_formatter=self.formatter,
            config=self._load_config()
        )
        self.callback_handlers = CallbackHandlers(
            command_handlers=self.command_handlers,
            message_formatter=self.formatter
        )
    
    def _load_config(self) -> dict:
        """Load bot configuration."""
        ...
    
    def build_application(self) -> Application:
        """Build telegram application with handlers."""
        app = Application.builder().token(self.token).build()
        
        # Register command handlers
        app.add_handler(CommandHandler("start", self.command_handlers.start))
        app.add_handler(CommandHandler("help", self.command_handlers.help))
        # ... other commands
        
        # Register callback handler
        app.add_handler(CallbackQueryHandler(self.callback_handlers.handle_callback))
        
        return app
    
    def run(self):
        """Start bot polling."""
        app = self.build_application()
        logger.info("Starting Telegram bot...")
        app.run_polling()
```

### Step 7: Validation (TODO #86)

**Actions**:
1. Run code_validator.py on all new modules
2. Verify line limits (< 500 lines each)
3. Run existing tests
4. Create new unit tests for each module
5. Achieve 80%+ coverage

**Commands**:
```bash
# Validate each module
python scripts/code_validator.py --file=src/infrastructure/telegram/bot_manager.py
python scripts/code_validator.py --file=src/infrastructure/telegram/handlers/command_handlers.py
python scripts/code_validator.py --file=src/infrastructure/telegram/handlers/callback_handlers.py
python scripts/code_validator.py --file=src/infrastructure/telegram/formatters/message_formatter.py

# Check line counts
wc -l src/infrastructure/telegram/bot_manager.py
wc -l src/infrastructure/telegram/handlers/*.py
wc -l src/infrastructure/telegram/formatters/*.py

# Run tests
pytest tests/infrastructure/telegram/ -v --cov
```

## SOLID Principles Applied

### Single Responsibility Principle (SRP)
- ✅ CommandHandlers: Only command logic
- ✅ CallbackHandlers: Only callback routing
- ✅ MessageFormatter: Only message formatting
- ✅ BotManager: Only bot orchestration

### Open/Closed Principle (OCP)
- ✅ New commands: Add method to CommandHandlers
- ✅ New callbacks: Add to callback_map
- ✅ New messages: Add to YAML config

### Liskov Substitution Principle (LSP)
- ✅ Can swap BinanceRESTClient with mock for testing
- ✅ Can swap DatabaseManager implementation

### Interface Segregation Principle (ISP)
- ✅ Handlers depend only on interfaces they use
- ✅ No fat interfaces

### Dependency Inversion Principle (DIP)
- ✅ Depend on abstractions (BinanceRESTClient interface)
- ✅ Inject dependencies, not create them
- ✅ Easy to test with mocks

## Cost Optimization Strategy

**Routing Decision**:
- Complexity: MEDIUM (code refactoring with clear patterns)
- Type: CODE (Python extraction and modularization)
- Token Estimate: 50K-80K tokens
- **Route**: Ollama (qwen2.5-coder:7b or :14b)
- **Cost**: $0.00 (vs ~$0.50 with API)

**Why Ollama**:
- Clear refactoring patterns
- Well-defined structure
- No complex reasoning needed
- Good quality with qwen2.5-coder
- 100% cost savings

**Use API only if**:
- Ollama output quality insufficient
- Complex architectural decisions needed
- User explicitly requests

## Success Metrics

- [ ] All files < 500 lines
- [ ] 0 hardcoded strings (all in YAML)
- [ ] 100% dependency injection
- [ ] 80%+ test coverage
- [ ] Passes code_validator.py
- [ ] Follows SOLID principles
- [ ] Token savings: 95%+ on config modifications

## Rollback Plan

Keep original file:
```bash
cp scripts/telegram_bot_hybrid.py scripts/telegram_bot_hybrid.py.backup
```

If issues:
```bash
mv scripts/telegram_bot_hybrid.py.backup scripts/telegram_bot_hybrid.py
rm -rf src/infrastructure/telegram/
```

## Migration Script

Create `scripts/migrate_to_new_bot.py`:
```python
"""Migration script from old bot to new architecture."""
from src.infrastructure.telegram.bot_manager import TelegramBotManager
# ... migration logic
```
