AI Web Terminal
Welcome to the AI Web Terminal, a fully functioning command-line interface built with a Python backend and a responsive web frontend. This application mimics the behavior of a real system terminal, allowing you to execute standard commands, manage files, and monitor system performance in real-time.

What makes this terminal special is its integrated AI command interpreter. You can type commands in plain English, and the terminal will translate them into the correct shell commands and execute them for you.

Features
Python Backend: Robust command processing built with Flask.

Full File & Directory Operations: ls, cd, pwd, mkdir, rm, touch, cat, and more.

AI Command Interpreter: Type what you want to do in English using the ai command (e.g., ai create a new file called report.txt).

Live System Stats Dashboard: A fixed header bar shows real-time CPU, memory, and disk usage, plus the top-running processes.

Theme Toggle: Switch between a sleek dark mode and a clean light mode with the click of a button.

Command History: Navigate your command history with the up and down arrow keys.

Auto-completion & Suggestions: See inline suggestions for commands as you type and use Tab to autocomplete.

Deployment-Ready: Includes a Procfile and requirements.txt for easy deployment to cloud platforms like Heroku.

Local Setup
To run this project on your local machine, follow these steps:

Prerequisites: Ensure you have Python 3 and pip installed.

Virtual Environment: It's highly recommended to create a virtual environment:

python3 -m venv venv
source venv/bin/activate

Install Dependencies: Install all the necessary packages from the requirements.txt file.

pip install -r requirements.txt

Set Environment Variable: The AI feature requires a Gemini API key. You need to set this as an environment variable.

export GEMINI_API_KEY="your_actual_api_key_here"

Note: Replace "your_actual_api_key_here" with your real key.

Run the Application:

python app.py

The terminal will be running at http://127.0.0.1:5050.

How to Deploy to Heroku
This application is configured for easy deployment to Heroku.

Prerequisites:

A free Heroku account.

The Heroku CLI installed on your machine.

Git installed on your machine.

Deployment Steps:

Login to Heroku: Open your system's terminal and run:

heroku login

This will open a browser window for you to log in.

Initialize Git Repository: If you haven't already, initialize a Git repository in your project folder.

git init
git add .
git commit -m "Initial commit"

Create a Heroku App: This command creates a new application on Heroku.

heroku create your-unique-app-name

(Replace your-unique-app-name with a name of your choice)

Set the AI API Key on Heroku: Just like you did locally, you must provide your API key to the live application.

heroku config:set GEMINI_API_KEY="your_actual_api_key_here" -a your-unique-app-name

Push to Heroku to Deploy: This command sends your code to Heroku, which will then build and deploy it automatically.

git push heroku master

(Note: Your main branch might be called main. If so, use git push heroku main)

Open Your App: Once the deployment is complete, you can open your live terminal in the browser with:

heroku open

That's it! Your AI Web Terminal is now live on the internet.
