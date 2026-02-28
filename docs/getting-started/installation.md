# Installation

This guide covers all the ways to install Chicory and its optional dependencies.

## Requirements

Chicory requires:

- **Python 3.11 or higher**
- **pip** or **uv** for package management

## Basic Installation

The basic installation includes core Chicory functionality with no broker or backend:

```bash
pip install chicory
```

!!! note
    The basic installation doesn't include any broker or backend. You'll need to install extras for full functionality.

## Installing with Extras

Chicory uses optional dependencies (extras) for different brokers and backends. Install only what you need:

### Redis Support

For Redis as both broker and backend:

```bash
pip install chicory[redis]
```

**Use case**: Simple setup, great for development and many production scenarios

### RabbitMQ Support

For RabbitMQ as a broker:

```bash
pip install chicory[rabbitmq]
```

**Use case**: Enterprise messaging, advanced routing, high reliability requirements

### PostgreSQL Support

For PostgreSQL as a backend:

```bash
pip install chicory[postgres]
```

**Use case**: When you already use PostgreSQL and want task results in your database

### MySQL Support

!!! warning "Experimental"
    MySQL backend support is **experimental and not tested**. Use at your own risk.

For MySQL as a backend:

```bash
pip install chicory[mysql]
```

### SQLite Support

!!! warning "Experimental"
    SQLite backend support is **experimental and not tested**. Use at your own risk.

For SQLite as a backend:

```bash
pip install chicory[sqlite]
```

### MS SQL Server Support

!!! warning "Experimental"
    MS SQL Server backend support is **experimental and not tested**. Use at your own risk.

For Microsoft SQL Server as a backend:

```bash
pip install chicory[mssql]
```

### CLI Support

For the command-line interface:

```bash
pip install chicory[cli]
```

### All Extras

To install everything:

```bash
pip install chicory[all]
```

This includes all brokers, backends, and the CLI.

**Use case**: Development, testing, or when you want maximum flexibility

## Combining Extras

You can install multiple extras at once:

```bash
# Redis broker + PostgreSQL backend + CLI
pip install chicory[redis,postgres,cli]

# RabbitMQ broker + Redis backend + CLI
pip install chicory[rabbitmq,redis,cli]
```

## Next Steps

Now that Chicory is installed, continue to:

- [Quick Start](quick-start.md) - Get running in 5 minutes
- [Tutorial](../tutorial/basic-usage.md) - Learn the basics
- [Tutorial](../tutorial/index.md) - In-depth guide
