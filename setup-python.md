# Set up a Python Project inside IntelliJ IDEA

## Setup Python Project
1. Goto the python service directory 
2. Create Virtual Environment run the following command
    python3.12 -m venv .venv
3. Activate the virtual environment
    source .venv/bin/activate
4. Install dependencies
    pip install -r requirements.txt
5. Install internal dependencies
   pip install -e ../chatcraft-common/
6Run the application
    python -m uvicorn app.main:app --host 0.0.0.0 --port <Port_Number>--reload --reload-dir app

## IDE Setup

1. Select File - Project Structure from the menu
2. Select Modules
3. Create a Module – The Python interpreter should be the python in ./venv/bin/python inside the project root
4. To run in the IDE, create a run Python run config as follows
5. In Use SDK Module select the module created earlier in step3
6. beneath SDK Module make sure module is selected and the value in the edit box should be uvicorn
7. Set the working directory to the directory containing the main.py file
7. 
