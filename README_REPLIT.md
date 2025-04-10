# Fireflies - Pronote Web Application

## Hosting on Replit

This application is configured to run on Replit. When you import this project into Replit:

1. The application will automatically use the correct port (8080) for Replit hosting
2. Dependencies will be installed from the requirements.txt file
3. The application will be accessible via your Replit URL

## Getting Started

1. Import this repository into Replit:
   - Go to [Replit](https://replit.com)
   - Click "Create Repl"
   - Choose "Import from GitHub" or upload your files
   - Select "Python" as the language

2. Set up the environment:
   - Run the setup script: `bash replit_setup.sh`
   - This will install dependencies and create necessary directories

3. Start the application:
   - Click the "Run" button
   - The application will start using `main.py` as the entry point
   - Access the application via the URL provided by Replit

## Configuration Files

The following files are used for Replit configuration:

- `main.py` - The entry point for the application on Replit
- `.replit` - Contains the run command and environment configuration
- `replit.nix` - Contains the Nix package configuration
- `pyproject.toml` - Contains the Poetry dependency configuration
- `replit.toml` - Alternative configuration format for Replit

## Troubleshooting

If you encounter the error "python: can't open file '/home/runner/workspace/undefined'":

1. Make sure you're using the correct configuration files:
   - Check that `.replit` points to `main.py` as the entry point
   - Try using the alternative configuration by renaming `.replit.new` to `.replit`

2. Try running the application manually:
   ```
   python3 main.py
   ```

3. Check file permissions:
   ```
   chmod +x main.py
   chmod +x pronote_web_app.py
   ```

4. Verify that all dependencies are installed:
   ```
   pip install -r requirements.txt
   ```

5. Make sure the application is listening on port 8080 (this is configured in `main.py`)

6. Check that the data directory is writable:
   ```
   mkdir -p data
   ```

## Additional Resources

- [Replit Python Documentation](https://docs.replit.com/programming-ide/getting-started-with-python)
- [Flask on Replit](https://docs.replit.com/tutorials/python/build-a-web-app-with-flask)