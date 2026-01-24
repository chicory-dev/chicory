"""
Example 2: Input Validation
============================

This example demonstrates Chicory's built-in validation features:
- Type validation with Pydantic
- INPUTS validation mode
- STRICT validation mode
- Validation errors and handling
- Optional parameters

Prerequisites:
--------------
1. Redis server running on localhost:6379
2. Worker running: chicory worker examples.shared_tasks:app

Usage:
------
    python examples/02_validation.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from chicory import ValidationError
from examples.shared_tasks import app, process_order, validate_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate input validation features."""

    logger.info("=" * 70)
    logger.info("CHICORY EXAMPLE 2: Input Validation")
    logger.info("=" * 70)

    await app.connect()

    try:
        # ====================================================================
        # 1. Valid input with strict validation
        # ====================================================================
        logger.info("1. Valid email validation (STRICT mode)...")
        result = await validate_email.delay(
            email="alice@example.com",
            user_id=123,
        )

        validation_result = await result.get(timeout=10.0)
        if validation_result is None:
            raise Exception("Task returned None unexpectedly")

        logger.info(f"   Email: {validation_result['email']}")
        logger.info(f"   Valid: {validation_result['is_valid']}")
        logger.info(f"   User ID: {validation_result['user_id']}")

        # ====================================================================
        # 2. Type validation - wrong type
        # ====================================================================
        logger.info("2. Type validation - passing wrong type...")
        try:
            # This should fail: user_id should be int, not string
            result = await validate_email.delay(
                email="bob@example.com",
                user_id="not_an_integer",  # Wrong type!
            )
            answer = await result.get(timeout=10.0)
            logger.info(f"   ✗ Should have failed but got: {answer}")
        except ValidationError as e:
            logger.info("   ✓ Validation error caught (expected):")
            logger.info(f"     {str(e)[:100]}...")

        # ====================================================================
        # 3. Missing required parameter
        # ====================================================================
        logger.info("3. Missing required parameter...")
        try:
            # This should fail: email is required
            result = await validate_email.delay(user_id=456)
            answer = await result.get(timeout=10.0)
            logger.info(f"   ✗ Should have failed but got: {answer}")
        except (ValidationError, TypeError) as e:
            logger.info("   ✓ Validation error caught (expected):")
            logger.info(f"     {str(e)[:100]}...")

        # ====================================================================
        # 4. Complex validation with optional parameters
        # ====================================================================
        logger.info("4. Order processing with optional parameters...")

        # Valid order with all parameters
        result = await process_order.delay(
            order_id="ORD-001",
            items=["laptop", "mouse", "keyboard"],
            total=1299.99,
            customer_email="customer@example.com",
        )

        order_result = await result.get(timeout=10.0)
        if order_result is None:
            raise Exception("Task returned None unexpectedly")

        logger.info("   Order processed:")
        logger.info(f"     - Order ID: {order_result['order_id']}")
        logger.info(f"     - Items: {order_result['item_count']}")
        logger.info(f"     - Total: ${order_result['total']:.2f}")
        logger.info(f"     - Email: {order_result['customer_email']}")
        logger.info(f"     - Status: {order_result['status']}")

        # ====================================================================
        # 5. Optional parameter omitted
        # ====================================================================
        logger.info("5. Order processing without optional email...")

        result = await process_order.delay(
            order_id="ORD-002",
            items=["book", "pen"],
            total=25.50,
            # customer_email is optional, omitted
        )

        order_result = await result.get(timeout=10.0)
        if order_result is None:
            raise Exception("Task returned None unexpectedly")

        logger.info("   Order processed:")
        logger.info(f"     - Order ID: {order_result['order_id']}")
        logger.info(f"     - Items: {order_result['item_count']}")
        logger.info(f"     - Total: ${order_result['total']:.2f}")
        logger.info(f"     - Email: {order_result['customer_email']}")  # Will be None

        # ====================================================================
        # 6. List type validation
        # ====================================================================
        logger.info("6. List type validation...")
        try:
            # This should fail: items should be a list, not a string
            result = await process_order.delay(
                order_id="ORD-003",
                items="this should be a list",  # Wrong type!
                total=99.99,
            )
            answer = await result.get(timeout=10.0)
            logger.info(f"   ✗ Should have failed but got: {answer}")
        except ValidationError as e:
            logger.info("   ✓ Validation error caught (expected):")
            logger.info("     Items must be a list")

        # ====================================================================
        # 7. Number type validation
        # ====================================================================
        logger.info("7. Number type validation...")
        try:
            # This should fail: total should be a float, not a string
            result = await process_order.delay(
                order_id="ORD-004",
                items=["item1", "item2"],
                total="not_a_number",  # Wrong type!
            )
            answer = await result.get(timeout=10.0)
            logger.info(f"   ✗ Should have failed but got: {answer}")
        except ValidationError as e:
            logger.info("   ✓ Validation error caught (expected):")
            logger.info("     Total must be a number")

        # ====================================================================
        # 8. Valid edge cases
        # ====================================================================
        logger.info("8. Valid edge cases...")

        # Empty list
        result = await process_order.delay(
            order_id="ORD-005",
            items=[],  # Empty list is valid
            total=0.0,
        )
        order_result = await result.get(timeout=10.0)
        if order_result is None:
            raise Exception("Task returned None unexpectedly")

        logger.info(f"   Empty order: {order_result['item_count']} items")

        # Very large number
        result = await process_order.delay(
            order_id="ORD-006",
            items=["yacht"],
            total=999999999.99,  # Large number
        )
        order_result = await result.get(timeout=10.0)
        if order_result is None:
            raise Exception("Task returned None unexpectedly")

        logger.info(f"   Large order: ${order_result['total']:,.2f}")

        logger.info("=" * 70)
        logger.info("All validation examples completed!")
        logger.info("=" * 70)

        logger.info("Key takeaways:")
        logger.info("  • Chicory validates input types automatically")
        logger.info("  • Use ValidationMode.INPUTS for input-only validation")
        logger.info("  • Use ValidationMode.STRICT for input+output validation")
        logger.info("  • Validation errors are caught before task execution")
        logger.info("  • Optional parameters work as expected")

    finally:
        await app.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
