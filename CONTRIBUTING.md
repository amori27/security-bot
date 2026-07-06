# Contributing

Thank you for your interest in contributing! We welcome contributions from everyone.

## How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/security-bot.git
cd security-bot

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install -r requirements-dev.txt
```

## Code Standards

- Follow PEP 8 style guide
- Write type hints for all functions
- Include docstrings for public APIs
- Keep functions focused and single-purpose
- Add unit tests for new functionality
- Ensure all tests pass before submitting

## Testing

```bash
pytest tests/ -v
pytest tests/ --cov=src
```

## Pull Request Process

1. Update README.md with details of changes if needed
2. Update CHANGELOG.md with your changes
3. Ensure CI passes (lint, type-check, test)
4. Get at least one review approval
5. Squash commits before merge

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Questions?

Open a [Discussion](https://github.com/amori27/security-bot/discussions) or [Issue](https://github.com/amori27/security-bot/issues).
