# Setting up Fireflies on Replit

## Step-by-Step Instructions

1. **Create a new Replit**
   - Go to [Replit](https://replit.com)
   - Click "Create Repl"
   - Select "Import from GitHub"
   - Paste your GitHub repository URL
   - Choose "Python" as the language
   - Click "Import from GitHub"

2. **Configure the Replit**
   - The `.replit` and `replit.nix` files are already configured
   - The application will automatically use port 8080 when running on Replit

3. **Run the Application**
   - Click the "Run" button
   - The application will start and be accessible via your Replit URL

4. **Persistent Data**
   - Replit provides persistent storage for your data
   - The application is configured to store data in the `data/` directory

5. **Environment Variables**
   - If you need to set environment variables:
     - Go to the "Secrets" tab in your Replit
     - Add key-value pairs for any environment variables

6. **Troubleshooting**
   - If you encounter issues with dependencies, try running:
     ```
     pip install -r requirements.txt
     ```
   - If you need to debug, check the console output in Replit
   - Make sure the application is listening on port 8080

7. **Making Changes**
   - You can edit files directly in the Replit editor
   - Changes will be saved automatically
   - Click "Run" to restart the application with your changes

8. **Sharing Your Application**
   - Your application will be available at your Replit URL
   - You can share this URL with others
   - You can also make your Replit public or private in the settings