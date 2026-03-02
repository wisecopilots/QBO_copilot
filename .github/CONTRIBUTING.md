# Contributing to QBO Copilot

Thanks for your interest in contributing. Here's how to get involved.

## Reporting Bugs

Open a [GitHub Issue](https://github.com/wisecopilots/QBO_copilot/issues) with:

- Steps to reproduce
- Expected vs. actual behavior
- Your environment (OS, Python version, QBO edition)
- Relevant log output or error messages

## Suggesting Features

Have an idea? Open an issue describing the problem you're trying to solve and your proposed approach.

## Development Setup

1. Fork and clone:

   ```bash
   git clone https://github.com/YOUR_USERNAME/QBO_copilot.git
   cd QBO_copilot
   ```

2. Run the setup script:

   ```bash
   bash setup.sh
   ```

   This creates a virtual environment, installs dependencies, and walks you through credential configuration.

3. Run tests against the QBO sandbox:

   ```bash
   python3 -m pytest tests/ -v
   ```

## Code Style

Format with [Black](https://github.com/psf/black) before submitting:

```bash
black .
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make focused changes (one feature or fix per PR)
3. Run the formatter: `black .`
4. Run tests if your changes touch QBO operations
5. Open a PR against `main` with a clear description

## Security

Never commit secrets, tokens, or credentials. The `config/.env` and `config/tokens/` directory are gitignored for this reason. If you discover a security vulnerability, please report it privately at jim@wisecopilots.com rather than opening a public issue.

## Code of Conduct

Be respectful and constructive in all interactions. Harassment, abusive language, and disrespectful behavior will not be tolerated.
