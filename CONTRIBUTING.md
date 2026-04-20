## Contributing to the API2Trade Python SDK

Thank you for your interest in contributing! 🎉

---

### What we need most

| Contribution type | Examples |
|-------------------|---------|
| **New language SDK wrappers** | PHP, C#, Ruby, Rust, Java |
| **More examples** | n8n workflow, Make (Integromat), Zapier webhooks |
| **Bot patterns** | Scalping bot, grid bot, VWAP strategy template |
| **Bug fixes** | See open Issues labeled `bug` |
| **Docs improvements** | Clearer docstrings, additional use-case walkthroughs |

---

### Development setup

```bash
git clone https://github.com/api2trade/api2trade-python-sdk.git
cd api2trade-python-sdk
pip install -e ".[dev]"
pytest tests/ -v
```

All tests use mocked HTTP — no real API key or live account required.

---

### Submitting a Pull Request

1. Fork the repo and create a branch: `git checkout -b feature/your-feature`
2. Make your changes with tests
3. Run `pytest tests/ -v` — all tests must pass
4. Open a PR against `main` with a clear description

---

### Code style

- Follow existing patterns in `api2trade_sdk/resources/`
- Add docstrings to all public methods
- Type hints on all function signatures

---

### Support

- 📧 [support@api2trade.com](mailto:support@api2trade.com)
- 💬 [t.me/apisupport_en](https://t.me/apisupport_en)
