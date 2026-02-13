# Contributing to QBO Copilot

Thank you for your interest in contributing to QBO Copilot! This guide will help you get started.

## Reporting Bugs

If you find a bug, please open an issue using the [Bug Report template](https://github.com/qbo-copilot/qbo-copilot/issues/new?template=bug_report.md). Include as much detail as possible:

- Steps to reproduce the issue
- Expected vs. actual behavior
- Your environment (OS, Python version, QBO sandbox or production)
- Relevant logs or screenshots

## Suggesting Features

Have an idea for a new feature? Open an issue using the [Feature Request template](https://github.com/qbo-copilot/qbo-copilot/issues/new?template=feature_request.md). Describe the problem you are trying to solve and your proposed approach.

## Development Setup

1. **Fork and clone the repository:**

   ```bash
   git clone https://github.com/YOUR_USERNAME/qbo-copilot.git
   cd qbo_copilot
   ```

2. **Create a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your environment:**

   ```bash
   cp config/.env.example config/.env
   cp config/clients.yaml.example config/clients.yaml
   ```

   Edit `config/.env` with your QBO OAuth credentials, Anthropic API key, and Slack tokens. Run `python3 qbo/oauth.py` to complete OAuth and obtain your `realm_id`, then update `config/clients.yaml`.

5. **Run tests against the QBO sandbox:**

   ```bash
   python3 -m pytest tests/ -v
   ```

## Code Style

This project uses [Black](https://github.com/psf/black) for code formatting. Please format your code before submitting a pull request:

```bash
black .
```

## Pull Request Process

1. **Fork** the repository and create a new branch from `main`:

   ```bash
   git checkout -b my-feature
   ```

2. **Make your changes.** Write clear, focused commits.

3. **Run the test suite** to make sure nothing is broken:

   ```bash
   python3 -m pytest tests/ -v
   ```

4. **Format your code:**

   ```bash
   black .
   ```

5. **Push your branch** and open a pull request against `main`. Fill out the PR template and describe what your changes do and why.

6. **Address review feedback.** A maintainer will review your PR. Be responsive to comments and requested changes.

## Security

Never commit secrets, tokens, or credentials. The `config/.env` and `config/tokens/` directory are gitignored for this reason. If you discover a security vulnerability, please report it privately rather than opening a public issue.

## Code of Conduct

Please be respectful and constructive in all interactions. We are committed to providing a welcoming and inclusive experience for everyone. Harassment, abusive language, and disrespectful behavior will not be tolerated.
