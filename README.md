# My Project

Build and query the database for the Knowledge base

## ToDo
* write tests
* add features from knowledgebaseinterface from replit agent


# To run the main program, first start the virtual environment, then execute the app module
## Create and install dependencies, if necessary
```sh
pyenv activate knowledge-base-explorer-env
```

## To build the database
Make sure local postgres server is running and the database name is configured in utils/config.py
```sh
python build_db.py 
```

```sh
python explorer/app.py
```
## Run in debug mode
```sh
python explorer/app.py -d
```
## To get help
```sh
python explorer/app.py -h
```

## Reference
https://docs.python-guide.org/writing/structure/


### _sample mermaid chart_
```mermaid
flowchart LR

A[Hard] -->|Text| B(Round)
B --> C{Decision}
C -->|One| D[Result 1]
C -->|Two| E[Result 2]
```
