# Tutorial

Welcome to the Chicory tutorial! This comprehensive guide will take you from basic task execution to advanced patterns.

## What You'll Learn

This tutorial covers:

1. **[Basic Usage](basic-usage.md)** - Task dispatch, results, and fire-and-forget
2. **[Input Validation](validation.md)** - Type safety and Pydantic integration
3. **[Retry Policies](retry-policies.md)** - Automatic retries with backoff strategies
4. **[Task Context](task-context.md)** - Access task metadata and control flow
5. **[Delivery Modes](delivery-modes.md)** - At-least-once vs at-most-once guarantees

## Prerequisites

Before starting this tutorial:

- Python 3.11+ installed
- Basic understanding of Python async/await
- Completed the [Quick Start](../getting-started/quick-start.md) guide

## Tutorial Format

Each section includes:

- **Concept explanation** - What it is and why it matters
- **Code examples** - Real, runnable code
- **Best practices** - How to use it effectively
- **Common pitfalls** - What to avoid

## Running the Examples

All examples in this tutorial are available in the `examples/` directory:

```bash
# Clone the repository
git clone https://github.com/chicory-dev/chicory.git
cd chicory

# Install dependencies
uv sync --all-extras

# Start Redis
docker run -d -p 6379:6379 redis:latest

# Run example workers (in separate terminals)
chicory worker examples.shared_tasks:app

# Run examples
python examples/01_basic_usage.py
python examples/02_validation.py
# ... and so on
```

## What's Next?

Start with [Basic Usage](basic-usage.md) and work through each section in order, or jump to topics that interest you.

Let's begin!
