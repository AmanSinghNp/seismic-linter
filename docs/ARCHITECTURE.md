# Architecture Overview

## Design Philosophy
seismic-linter follows a modular architecture with three main components:

1. **Static Analyzer**: AST-based code inspection
2. **Runtime Hooks**: Decorator-based validation
3. **Testing Integration**: Pytest helpers

## Component Diagram

```mermaid
graph TD
    CLI[CLI (cli.py)] --> Config[Config Loader (config.py)]
    CLI --> Collect[File Collector]
    CLI --> Manager[Parallel Manager]
    Manager --> Worker1[Worker Process]
    Manager --> Worker2[Worker Process]
    
    subgraph "Worker Process"
        Wrapper[Runner Wrapper] --> Runner[runner.py]
        Runner --> Cache[Cache Access (caching.py)]
        Runner --> Parser[Notebook Parser (notebook_handler.py)]
        Runner --> Analyzer[AST Analyzer (analyzer.py)]
        Analyzer --> Rules[Rules Registry (rules.py)]
    end
    
    Runtime[Runtime Hooks (runtime.py)] -.-> Data[User Data]
```

## Key Design Decisions
- **AST Parsing over Regex**: We use `ast` instead of regex to reliably parse Python syntax, handle multiline statements, and traverse chained calls, ensuring lower false positive rates.
- **Parallel Architecture**: A Manager-Worker pattern using `ProcessPoolExecutor` allows efficient processing of large repositories and CPU-intensive notebook parsing.
- **Caching Strategy**: We use content hashing (MD5) to skip analysis of unchanged files. Cache is file-based to survive restarts.
- **Decorator Pattern for Runtime**: Decorators allow users to opt-in to runtime checks without changing their core function logic.

## Extension Points
- **Adding Rules**: Define a new `Rule` in `rules.py` and implement the detection logic in `analyzer.py` (e.g., `visit_Call`).
- **Support New File Types**: Extend `collect_files` in `cli.py` and implement a parser in a handler module.
- **Output Formats**: Add new formatters in `cli.py` (e.g. `print_json`, `print_github`).
