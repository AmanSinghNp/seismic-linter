# Architecture Overview

## Design Philosophy
seismic-linter follows a modular architecture with three main components:

1. **Static Analyzer**: AST-based code inspection
2. **Runtime Hooks**: Decorator-based validation
3. **Testing Integration**: Pytest plugin

## Component Diagram
[Add diagram later]

## Key Design Decisions
- Why AST parsing over regex
- Why decorator pattern for runtime validation
- Trade-offs in detection accuracy vs false positives

## Extension Points
How to add new rules, custom detectors, etc.
