# Running Fireflies on Replit

If you're encountering the error "python: can't open file '/home/runner/workspace/undefined'", follow these simple steps:

## Option 1: Run directly in the Replit Shell

1. Open the Shell in Replit (click on the "Shell" tab)
2. Run the following command:
   ```
   python main.py
   ```

## Option 2: Use the run.sh script

1. Open the Shell in Replit
2. Run the following command:
   ```
   bash run.sh
   ```

## Option 3: Fix the Replit configuration

1. Make sure the `.replit` file contains only these two lines:
   ```
   run = "python main.py"
   language = "python3"
   ```

2. Click the "Run" button in Replit

## Troubleshooting

If you still encounter issues:

1. Check that `main.py` exists in your project root
2. Try installing dependencies manually:
   ```
   pip install -r requirements.txt
   ```
3. Make sure you're in the correct directory:
   ```
   pwd
   ls -la
   ```
4. If needed, create a new Repl and import your project again