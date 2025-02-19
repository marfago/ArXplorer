# ArXplorer

[![CI](https://github.com/marfago/ArXplorer/actions/workflows/ci.yml/badge.svg)](https://github.com/marfago/ArXplorer/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

ArXplorer is an advanced system for searching, retrieving, and analyzing academic papers from arXiv. It uses AI-powered
agents to perform intelligent searches, assess paper relevance, and extract references, providing researchers with a
powerful tool for literature review and discovery.

## Key Features

- Natural Language Query Processing
- Automated Paper Retrieval and Analysis
- Reference and Citation Management
- Multi-threaded Architecture
- Data Persistence and Management
- User-friendly Interface

## Installation

1. Install ArXplorer using pip:

```bash
pip install arxplorer
```

2. Set up the Google Gemini API key and/or Groq API key:

   You need to set the GEMINI_API_KEY and/or GROQ_API_KEY as environment variables. Follow the instructions for your operating system:

   ### Windows:

   Open Command Prompt and run:
   ```
   setx GEMINI_API_KEY "your_gemini_api_key_here"
   setx GROQ_API_KEY "your_groq_api_key_here"
   ```
   Close and reopen Command Prompt for the changes to take effect.

   ### macOS and Linux:

   Add the following line to your shell configuration file (e.g., `~/.bash_profile`, `~/.bashrc`, or `~/.zshrc`):
   ```
   export GEMINI_API_KEY="your_gemini_api_key_here"
   export GROQ_API_KEY="your_groq_api_key_here"
   ```
   Then, either restart your terminal or run:
   ```
   source ~/.bash_profile  # or ~/.bashrc, or ~/.zshrc
   ```

   ### Verifying the Environment Variable:

   To verify that the environment variable is set correctly, you can run:

   - On Windows (Command Prompt):
     ```
     echo %GEMINI_API_KEY%
     ```
     or
     ```
     echo %GROQ_API_KEY%
     ```

   - On macOS and Linux:
     ```
     echo $GEMINI_API_KEY
     ```
     or
     ```
     echo $GROQ_API_KEY$
     ```

   This should display your API key.

## Quick Start

1. Run ArXplorer:
   ```bash
   arxplorer
   ```

   This will start the ArXplorer server. By default, it runs on `0.0.0.0:6007`, which means it's accessible from any IP
   address on port 6007.

2. Access the ArXplorer interface by opening a web browser and navigating to:
   ```
   http://localhost:6007
   ```

   If you're accessing it from another device on the same network, replace `localhost` with the IP address of the
   machine running ArXplorer.

Note: The default address (0.0.0.0) allows connections from any IP. If you want to restrict access to only the local
machine, you can use 127.0.0.1 instead.

## Documentation

For detailed usage instructions and system architecture, please refer to our [DEVELOPMENT.md](DEVELOPMENT.md) file.

## Development

For information on setting up a development environment, running tests, and contributing to the project, please see
our [DEVELOPMENT.md](DEVELOPMENT.md) file.

## Contributing

Contributions are welcome! Please see our [Contribution Guidelines](CONTRIBUTING.md) for more details.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.