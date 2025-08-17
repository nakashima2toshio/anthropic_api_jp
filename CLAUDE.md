# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Anthropic API demonstration and learning project featuring comprehensive Python examples showcasing various Claude API capabilities. The project includes interactive Streamlit applications demonstrating text generation, structured outputs, image processing, audio handling, conversation management, and chain-of-thought reasoning.

## Development Commands

### Running Applications
```bash
# Main unified demo
streamlit run a10_00_responses_api.py --server.port=8501

# Structured outputs demo
streamlit run a10_01_structured_outputs_parse_schema.py --server.port=8501

# Tools & Pydantic parse demo
streamlit run a10_02_responses_tools_pydantic_parse.py --server.port=8502

# Images & vision demo
streamlit run a10_03_images_and_vision.py --server.port=8503

# Audio processing demo
streamlit run a10_04_audio_speeches.py --server.port=8504

# Conversation state management demo
streamlit run a10_05_conversation_state.py --server.port=8505

# Chain of thought demo
streamlit run a10_06_reasoning_chain_of_thought.py --server.port=8506
```

### Testing
```bash
# Run all tests with verbose output
pytest -v

# Run tests with coverage
pytest --cov

# Run specific test categories (defined in pytest.ini)
pytest -m unit      # Unit tests
pytest -m api       # API tests  
pytest -m slow      # Long-running tests
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Required environment variables
export ANTHROPIC_API_KEY='your-anthropic-api-key'

# Optional (for specific demos)
export OPENWEATHER_API_KEY='your-openweather-api-key'
export EXCHANGERATE_API_KEY='your-exchangerate-api-key'
```

## Code Architecture

### Core Helper Modules
- **`helper_api.py`**: Unified Anthropic API wrapper with client management, token counting, response processing, and configuration handling
- **`helper_st.py`**: Streamlit UI components and session state management for consistent user interface across all demos

### Configuration System
- **`config.yml`**: Central configuration file containing:
  - Model definitions and categorization (flagship, balanced, fast, vision, coding)
  - Pricing information for cost tracking
  - API settings (timeout, retries, limits)
  - UI preferences and internationalization
  - Logging configuration

### Demo Applications Structure
Each demo follows a consistent pattern:
1. Import unified helper modules (`helper_api.py`, `helper_st.py`)
2. Initialize session state and configuration
3. Render UI components using helper classes
4. Process API calls through centralized client
5. Display results with consistent formatting

### Key Classes and Components

#### ConfigManager (helper_api.py)
- Singleton pattern for configuration management
- YAML-based configuration with environment variable support
- Model categorization and pricing information

#### AnthropicClient (helper_api.py)
- Centralized API client with retry logic and error handling
- Token counting and cost estimation
- Response processing and caching

#### UIHelper Classes (helper_st.py)
- `MessageManagerUI`: Conversation history display
- `ResponseProcessorUI`: API response formatting
- `SessionStateManager`: Persistent state management
- `InfoPanelManager`: Standardized information panels

### Data Management
- **`data/`**: Contains sample files for testing (images, audio, text, JSON data)
- **`utils/`**: Utility scripts for data processing, web scraping, and API interactions

### Documentation
- **`doc/`**: Comprehensive documentation including API usage patterns, test plans, and helper function references
- **`README.md`**: Complete project overview with feature descriptions and setup instructions

## Development Patterns

### Error Handling
All API calls use consistent error handling patterns with fallback mechanisms and user-friendly error messages in both Japanese and English.

### Session State Management
Streamlit session state is managed centrally through `SessionStateManager` to maintain conversation history, API responses, and user preferences across page refreshes.

### API Response Processing
Responses are processed through `ResponseProcessor` classes that handle:
- Token counting and cost calculation
- Response formatting and validation
- Caching for repeated requests
- Structured output parsing

### Configuration-Driven Development
Models, API settings, and UI preferences are configured through `config.yml`, making it easy to:
- Switch between different Claude models
- Adjust API parameters without code changes
- Customize UI behavior per environment
- Track usage costs across different models

## Testing Infrastructure

The project uses pytest with custom markers for different test categories:
- `unit`: Basic functionality tests
- `integration`: Multi-component tests
- `api`: Tests requiring API calls
- `ui`: User interface tests
- `functional`: End-to-end functionality tests
- `performance`: Performance benchmarking tests
- `slow`: Time-intensive tests

Test configuration is managed through `pytest.ini` with specific test paths and output formatting.