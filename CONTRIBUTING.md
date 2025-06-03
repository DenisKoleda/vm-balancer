# Contributing to VMManager 6 Auto-Balancer

Thank you for your interest in contributing to the VMManager 6 Auto-Balancer! We welcome contributions from the community.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/vm_balancer.git
   cd vm_balancer
   ```
3. **Set up development environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 📝 Development Guidelines

### Code Style
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings for all functions and classes
- Keep functions focused and reasonably sized
- Use type hints where appropriate

### Code Quality
- Write clean, readable code
- Add comments for complex logic
- Ensure all new code is tested
- Run existing tests to ensure nothing breaks
- Use descriptive commit messages

### Documentation
- Update README.md if you add new features
- Add docstrings for new functions/classes
- Update configuration examples if needed
- Keep comments in English

## 🐛 Reporting Issues

Before creating a new issue, please:

1. **Search existing issues** to avoid duplicates
2. **Use the latest version** to ensure the issue still exists
3. **Provide detailed information**:
   - VMManager version
   - Python version
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant log output
   - Configuration details (sanitized)

## 💡 Suggesting Features

We welcome feature suggestions! Please:

1. **Check existing issues** and discussions
2. **Open a discussion** first for major features
3. **Provide context** about your use case
4. **Consider implementation complexity**
5. **Be open to feedback** and discussion

## 🔧 Pull Request Process

### Before Submitting
- [ ] Test your changes thoroughly
- [ ] Update documentation if needed
- [ ] Add tests for new functionality
- [ ] Ensure all existing tests pass
- [ ] Follow the code style guidelines
- [ ] Write clear commit messages

### Pull Request Description
Please include:
- **Clear description** of changes
- **Motivation** for the change
- **Testing performed**
- **Screenshots** (if applicable)
- **Breaking changes** (if any)
- **Related issues** (if any)

### Review Process
1. Automated checks will run on your PR
2. Code review by maintainers
3. Address any feedback
4. Approval and merge

## 🧪 Testing

### Manual Testing
- Test with a VMManager development environment
- Use `--dry-run` mode for safe testing
- Test different configuration scenarios
- Verify logging output

### Test Coverage Areas
- API authentication and connectivity
- Node and VM information parsing
- Load balancing logic
- Migration decision making
- Error handling
- Configuration validation

## 📋 Code of Conduct

### Our Standards
- **Be respectful** and inclusive
- **Be constructive** in discussions
- **Focus on the code** and technical aspects
- **Help others learn** and grow
- **Follow project guidelines**

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or insulting comments
- Personal attacks
- Publishing private information
- Other unprofessional conduct

## 🏷️ Commit Message Convention

Use descriptive commit messages:

```
feat: add cluster filtering by node capacity
fix: handle API timeout errors gracefully
docs: update installation instructions
refactor: simplify VM selection logic
test: add unit tests for load calculation
```

## 📚 Development Tips

### Local Development
- Use a test VMManager environment
- Start with `--dry-run` mode
- Monitor logs during development
- Test edge cases and error conditions

### Debugging
- Enable DEBUG logging level
- Use the interactive mode for testing
- Check VMManager API documentation
- Validate API responses

### Common Patterns
- Always check API response status
- Handle exceptions gracefully
- Log important actions and decisions
- Use dataclasses for structured data
- Validate configuration parameters

## 🎯 Areas for Contribution

We especially welcome contributions in these areas:

### Features
- Enhanced load balancing algorithms
- Additional safety checks
- Performance monitoring integration
- Web interface
- Configuration validation
- Advanced scheduling options

### Infrastructure
- Unit and integration tests
- CI/CD improvements
- Documentation enhancements
- Code quality tools
- Performance optimizations

### Documentation
- API documentation
- Deployment guides
- Troubleshooting guides
- Video tutorials
- Translation to other languages

## 🤝 Community

- **GitHub Discussions**: For questions and feature discussions
- **GitHub Issues**: For bug reports and feature requests
- **Pull Requests**: For code contributions
- **Wiki**: For additional documentation

## 📞 Getting Help

If you need help:

1. Check the documentation and FAQ
2. Search existing issues and discussions
3. Ask in GitHub Discussions
4. Contact maintainers if needed

Thank you for contributing to VMManager 6 Auto-Balancer! 🙏 