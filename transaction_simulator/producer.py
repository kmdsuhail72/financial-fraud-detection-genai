"""
Transaction Simulator Producer Integration with Kinesis Streaming.
"""
from streaming.producer import TransactionStreamProducer, main

__all__ = ["TransactionStreamProducer", "main"]

if __name__ == "__main__":
    main()
