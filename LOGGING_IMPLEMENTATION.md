# Logging Framework Implementation Guide

## 📋 Overview

This PR implements a comprehensive logging framework to replace `print()` statements throughout the HotWalletClaimer codebase.

## ✅ What's Been Added

### 1. **StructuredLogger Class** (`games/utils/logger.py`)

A production-ready logging system with:

#### Features:
- ✅ Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- ✅ Color-coded console output
- ✅ File output with timestamps
- ✅ Context logging with structured data
- ✅ Game-specific loggers
- ✅ Configurable handlers
- ✅ UTF-8 encoding support

#### Usage:
```python
from games.utils.logger import get_game_logger

# Get game-specific logger
logger = get_game_logger('Hot')

logger.info("Claim started", game="Hot", claim_id="12345")
logger.error("Login failed", error="Timeout", retries=3)
logger.debug_context({"user": "user123", "step": 1})
```

### 2. **Color-Coded Output**

```
[2026-01-28 19:15:30] INFO - Claim started (from games/hot.py:456)
[2026-01-28 19:15:31] ERROR - Login failed (from games/hot.py:457)
[2026-01-28 19:15:32] DEBUG - Context: { ... } (from games/hot.py:458)
```

### 3. **Context Logging**

```python
logger.info_context({
    "user": "user123",
    "wallet_id": "Wallet1",
    "claim_id": "abc123",
    "status": "success"
})
```

## 📊 Benefits

| Before | After |
|--------|-------|
| No log levels | 5 levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| No timestamps | Full timestamps (YYYY-MM-DD HH:MM:SS) |
| No context | Structured context with key-values |
| No file logging | Optional file logging with rotation |
| Hard to debug | Easy to filter and search logs |
| No color coding | Color-coded for easy scanning |
| Mixed severity | Proper log level separation |

## 🎯 Migration Guide

### Step 1: Replace `print()` with `logger.info()`

```python
# Before
print(f"Step {self.step} - Claim started")

# After
logger.info(f"Step {self.step} - Claim started")
```

### Step 2: Replace `print(f"Error: {e}")` with `logger.error()`

```python
# Before
print(f"Error: {e}")

# After
logger.error(f"Error: {e}", error=str(e))
```

### Step 3: Replace `print(f"Step {self.step} - {message}")` with `logger.info()`

```python
# Before
print(f"Step {self.step} - {message}")

# After
logger.info(f"Step {self.step} - {message}")
```

### Step 4: Use context logging for structured data

```python
# Before
print(f"User: {user}, Step: {step}, Status: {status}")

# After
logger.info_context({
    "user": user,
    "step": step,
    "status": status
})
```

### Step 5: Use debug logging for detailed information

```python
# Before
print(f"DEBUG: Element found at {element.location}")

# After
logger.debug(f"Element found at {element.location}", element_location=element.location)
```

## 📝 Example Usage in Existing Code

### Example 1: Hot Game

```python
from games.utils.logger import get_game_logger

logger = get_game_logger('Hot')

def full_claim(self):
    logger.info("Starting claim process")
    logger.debug_context({"game": "Hot", "wallet": self.wallet_id})

    try:
        logger.info("Attempting login")
        # ... login logic ...
        logger.info("Login successful", user=self.wallet_id)
    except Exception as e:
        logger.error("Login failed", error=str(e), exception_type=type(e).__name__)
        raise
```

### Example 2: HamsterKombat

```python
from games.utils.logger import get_game_logger

logger = get_game_logger('HamsterKombat')

def get_balance(self, claimed=False):
    try:
        balance = self.monitor_element(xpath, timeout=10)
        logger.debug(f"Balance found: {balance.text}", balance=balance.text)
        return float(balance.text)
    except TimeoutException:
        logger.error("Balance not found", xpath=xpath, timeout=10)
        return None
```

## 🔧 Configuration

### Console Output Only
```python
logger = StructuredLogger("MyApp", console_output=True, log_file=None)
```

### File Logging
```python
logger = StructuredLogger(
    "MyApp",
    log_file="logs/app.log",
    console_output=True
)
```

### Specific Log Level
```python
logger = StructuredLogger(
    "MyApp",
    log_level=logging.DEBUG  # Show all levels
)
```

## 📈 Log File Structure

```
logs/
├── hot-2026-01-28.log
├── hamsterkombat-2026-01-28.log
├── blum-2026-01-28.log
└── overall.log
```

Each file contains:
- Timestamps
- Log levels with colors (in console)
- Source file and line number
- Structured context data
- UTF-8 encoded

## 🎨 Color Coding

| Level | Color | Usage |
|-------|-------|-------|
| DEBUG | Cyan | Detailed debugging information |
| INFO | Green | General information (default) |
| WARNING | Yellow | Non-critical issues |
| ERROR | Red | Errors that need attention |
| CRITICAL | Magenta | Critical errors causing failures |

## 📊 Performance Impact

- **Minimal**: StructuredLogger uses Python's built-in logging module
- **No overhead**: Only logs at configured levels
- **Fast**: Simple text formatting

## 🔄 Backward Compatibility

✅ **100% backward compatible** - Existing code continues to work without changes

The logging framework is **optional** - you can use it alongside `print()` or replace it gradually.

## 📝 Best Practices

### When to Use Each Level

**DEBUG**: Detailed information for debugging
```python
logger.debug("Element found", element=element)
logger.debug("User input received", input=user_input)
```

**INFO**: General information (default level)
```python
logger.info("Claim started", wallet_id=wallet_id)
logger.info("Step completed", step=step, status="success")
```

**WARNING**: Non-critical issues
```python
logger.warning("Element took long to load", xpath=xpath, timeout=30)
logger.warning("Retrying operation", attempt=2, max_attempts=3)
```

**ERROR**: Errors that should be fixed
```python
logger.error("Login failed", error=str(e), exception_type=type(e).__name__)
logger.error("Balance not found", xpath=xpath)
```

**CRITICAL**: Critical errors
```python
logger.critical("WebDriver crashed", error=str(e))
logger.critical("Session expired, cannot continue")
```

## 📚 Related Files

- `games/utils/logger.py` - Main logging implementation
- `SECURITY_ENHANCEMENTS.md` - Security utilities (previous PR)
- `games/utils.py` - Security and error handling utilities (previous PR)

## 🎯 Impact Summary

| Category | Improvement |
|----------|-------------|
| **Debugging** | Easy log filtering and search |
| **Maintenance** | Better error tracking |
| **Observability** | Structured context logging |
| **User Experience** | Color-coded, readable output |
| **Logging** | File output + console + rotation support |
| **Language** | All documentation in English |

## ✅ Testing Checklist

- [x] Logger initialization
- [x] Console output with colors
- [x] File output
- [x] Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- [x] Context logging
- [x] Multiple game loggers
- [x] Timestamp formatting
- [x] Source file tracking
- [x] UTF-8 encoding

## 🚀 Next Steps

1. Review the logging framework implementation
2. Test with your game implementations
3. Gradually replace `print()` statements with logger calls
4. Configure log files in settings
5. Monitor log files for issues

## 📞 Support

For questions or issues:
- Review the code in `games/utils/logger.py`
- Check the usage examples above
- Use debug context for troubleshooting

---

**Created**: January 28, 2026
**Language**: English
**Status**: Ready for review and deployment
