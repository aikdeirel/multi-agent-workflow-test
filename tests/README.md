# Multi-Agent System Test Suite

This directory contains comprehensive unit and integration tests for the multi-agent orchestration system.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── unit/                    # Unit tests
│   ├── test_config.py      # Configuration module tests
│   ├── test_prompt_manager.py # Prompt management tests
│   ├── test_weather_tools.py  # Weather tools tests
│   ├── test_main.py        # FastAPI application tests
│   └── test_agent_factory.py # Agent creation and management tests
├── integration/             # Integration tests (future)
├── fixtures/               # Test data and fixtures (future)
└── README.md               # This file
```

## Test Categories

### Unit Tests (`pytest.mark.unit`)
- **Configuration Tests**: Settings validation, JSON loading, environment variables
- **Prompt Manager Tests**: Prompt loading, file management, error handling
- **Weather Tools Tests**: API interactions, data formatting, geocoding
- **Main Application Tests**: FastAPI endpoints, request/response handling, middleware
- **Agent Factory Tests**: Agent creation, LLM configuration, operator management

### Integration Tests (`pytest.mark.integration`)
- Cross-component functionality
- End-to-end workflows
- Real API interactions (mocked for unit tests)

### Test Markers
- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, cross-component)
- `@pytest.mark.slow` - Slow tests (can be skipped for quick runs)
- `@pytest.mark.external` - Tests requiring external dependencies
- `@pytest.mark.mock` - Tests with extensive mocking

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
cd src
pip install -r requirements.txt
```

2. Set environment variables (for tests that need them):
```bash
export LANGFUSE_PUBLIC_KEY=pk-lf-test-key
export LANGFUSE_SECRET_KEY=sk-lf-test-secret
export MISTRAL_API_KEY=test-mistral-key
```

### Running All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing
```

### Running Specific Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests  
pytest -m integration

# Run tests excluding slow ones
pytest -m "not slow"

# Run only mocked tests
pytest -m mock
```

### Running Specific Test Files

```bash
# Run config tests only
pytest tests/unit/test_config.py

# Run specific test class
pytest tests/unit/test_config.py::TestSettings

# Run specific test method
pytest tests/unit/test_config.py::TestSettings::test_settings_with_valid_env_vars
```

### Parallel Test Execution

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Run with specific number of workers
pytest -n 4
```

## Test Configuration

### pytest.ini Configuration

The test suite is configured with:
- **Coverage**: Minimum 85% coverage requirement
- **Strict markers**: All markers must be defined
- **Warning filters**: Suppress known library warnings
- **HTML reports**: Coverage reports in `htmlcov/`

### Fixtures

Key fixtures available in `conftest.py`:

#### Environment and Configuration
- `mock_env_vars` - Mock environment variables
- `mock_settings` - Mock settings object
- `mock_json_configs` - Mock JSON configuration files

#### External Services  
- `mock_langfuse_client` - Mock Langfuse client
- `mock_llm` - Mock ChatMistralAI LLM
- `mock_weather_api` - Mock weather API responses

#### Test Data
- `sample_weather_data` - Sample weather API response
- `sample_location_info` - Sample location data
- `temp_prompts_dir` - Temporary prompt directory
- `temp_settings_dir` - Temporary settings directory

#### Application Components
- `mock_agent_executor` - Mock agent executor
- `test_client` - FastAPI test client

#### Parametrized Fixtures
- `sample_locations` - Various location formats
- `sample_weather_conditions` - Different weather scenarios
- `sample_math_expressions` - Mathematical expressions
- `sample_dates` - Date format variations

## Coverage Goals

### Current Coverage Targets

| Module | Target | Status |
|--------|--------|--------|
| `config.py` | 95% | ✅ |
| `prompt_manager.py` | 90% | ✅ |
| `weather_operator.py` | 85% | ✅ |
| `main.py` | 80% | ✅ |
| `agent_factory.py` | 85% | ✅ |

### Coverage Report

Generate detailed coverage reports:

```bash
# Terminal report
pytest --cov=src --cov-report=term-missing

# HTML report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# XML report (for CI)
pytest --cov=src --cov-report=xml
```

## Test Data and Mocking

### Mocking Strategy

The test suite uses comprehensive mocking to ensure:
- **Isolation**: Tests don't depend on external services
- **Speed**: Fast execution without network calls
- **Reliability**: Consistent test results
- **Control**: Predictable test scenarios

### Key Mocked Components

1. **External APIs**
   - Weather APIs (Open-Meteo)
   - Langfuse tracing service
   - Mistral LLM API

2. **File System**
   - Configuration files
   - Prompt files
   - Temporary directories

3. **Environment**
   - Environment variables
   - System paths
   - Network conditions

### Test Data

Sample data includes:
- Weather API responses
- Location geocoding data
- Agent execution results
- Configuration examples
- Error scenarios

## Best Practices

### Writing Tests

1. **Descriptive Names**: Test names should clearly describe what's being tested
2. **Arrange-Act-Assert**: Follow the AAA pattern
3. **One Assertion**: Focus on testing one thing per test
4. **Mock External Dependencies**: Don't make real API calls
5. **Use Fixtures**: Leverage shared fixtures for common setup

### Test Organization

1. **Group Related Tests**: Use test classes to group related functionality
2. **Mark Tests Appropriately**: Use pytest markers for categorization
3. **Isolate Tests**: Each test should be independent
4. **Clean Up**: Use fixtures for setup and teardown

### Parametrized Tests

Use `@pytest.mark.parametrize` for testing multiple scenarios:

```python
@pytest.mark.parametrize("location,expected", [
    ("Berlin", "Germany"),
    ("London", "UK"),
    ("New York", "USA"),
])
def test_location_parsing(location, expected):
    result = parse_location(location)
    assert expected in result
```

## Continuous Integration

### GitHub Actions Integration

The test suite is designed to work with CI/CD:

```yaml
- name: Run tests
  run: |
    pytest --cov=src --cov-report=xml --cov-fail-under=85
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
```

### Quality Gates

Tests must pass these quality gates:
- All tests pass
- Coverage >= 85%
- No linting errors
- No security vulnerabilities

## Debugging Tests

### Common Issues

1. **Import Errors**: Ensure `src/` is in Python path
2. **Fixture Conflicts**: Check fixture scope and dependencies
3. **Mock Leakage**: Ensure mocks are properly isolated
4. **Flaky Tests**: Look for timing issues or shared state

### Debugging Commands

```bash
# Run tests with debugging
pytest --pdb

# Run with print statements
pytest -s

# Show local variables on failure
pytest --tb=long

# Run specific test with maximum verbosity
pytest -vvv tests/unit/test_config.py::test_specific_function
```

### Debugging Fixtures

```bash
# Show fixture setup/teardown
pytest --setup-show

# Show available fixtures
pytest --fixtures
```

## Performance Testing

### Benchmark Tests

Some tests include performance benchmarks:

```python
def test_prompt_loading_performance(benchmark):
    result = benchmark(load_prompt, "large_prompt")
    assert len(result) > 0
```

### Memory Testing

Monitor memory usage during tests:

```bash
# Run with memory profiling
pytest --memray

# Generate memory report
memray flamegraph test_results.bin
```

## Future Enhancements

### Planned Additions

1. **Property-Based Testing**: Using Hypothesis for edge case generation
2. **Mutation Testing**: Using mutmut to test test quality
3. **Load Testing**: Using locust for API endpoint testing
4. **Contract Testing**: Using pact for API contract validation
5. **Visual Testing**: Screenshot comparison for UI components

### Test Data Expansion

- More weather scenarios
- Additional location formats
- Complex agent interactions
- Error condition variations
- Edge case collections

## Contributing

### Adding New Tests

1. Create test file following naming convention: `test_<module>.py`
2. Use appropriate fixtures from `conftest.py`
3. Add proper pytest markers
4. Include docstrings explaining test purpose
5. Ensure good coverage of edge cases

### Test Review Checklist

- [ ] Tests are independent and isolated
- [ ] Proper use of fixtures and mocking
- [ ] Descriptive test names and docstrings
- [ ] Good coverage of happy path and edge cases
- [ ] Appropriate pytest markers
- [ ] No hardcoded values or magic numbers
- [ ] Tests run quickly (< 1s per test)

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Hypothesis Testing](https://hypothesis.readthedocs.io/)

## Support

For questions about the test suite:
1. Check this README
2. Review existing test patterns
3. Check pytest documentation
4. Ask in team chat or create an issue