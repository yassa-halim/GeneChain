import zlib
import logging
import time
from typing import Union, Optional

# Setup logging for better debugging and tracing
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Base class for compressors
class Compressor:
    def __init__(self, compression_level: Optional[int] = 6) -> None:
        """
        Initializes the Compressor object.
        
        :param compression_level: The level of compression, default is 6 (range 0-9)
        """
        self.compression_level = compression_level
        logger.debug(f"Compressor initialized with compression level {self.compression_level}")

    def compress(self, data: Union[str, bytes]) -> bytes:
        """
        Compress data. Must be implemented by subclasses.
        
        :param data: Data to compress (str or bytes)
        :return: Compressed data as bytes
        """
        raise NotImplementedError("Subclasses must implement this method")

    def decompress(self, compressed_data: bytes) -> str:
        """
        Decompress data. Must be implemented by subclasses.
        
        :param compressed_data: Data to decompress (bytes)
        :return: Decompressed data as string
        """
        raise NotImplementedError("Subclasses must implement this method")


# ZLIB Compressor Implementation
class ZLIBCompressor(Compressor):
    def __init__(self, compression_level: Optional[int] = 6) -> None:
        """
        ZLIB-specific compressor that uses zlib library for compression.
        
        :param compression_level: The level of compression, default is 6
        """
        super().__init__(compression_level)
        logger.debug("ZLIBCompressor initialized")

    def compress(self, data: Union[str, bytes]) -> bytes:
        """
        Compress data using zlib.
        
        :param data: Data to compress (str or bytes)
        :return: Compressed data as bytes
        """
        if isinstance(data, str):
            data = data.encode('utf-8')  # Convert string to bytes
            logger.debug("Data encoded to bytes for compression")
        elif not isinstance(data, bytes):
            raise ValueError("Input data must be of type 'str' or 'bytes'")

        logger.debug("Starting compression with ZLIB")
        compressed_data = zlib.compress(data, self.compression_level)
        logger.debug(f"Compression completed, compressed size: {len(compressed_data)} bytes")
        return compressed_data

    def decompress(self, compressed_data: bytes) -> str:
        """
        Decompress data using zlib.
        
        :param compressed_data: Compressed data as bytes
        :return: Decompressed data as string
        """
        logger.debug(f"Starting decompression, compressed size: {len(compressed_data)} bytes")
        decompressed_data = zlib.decompress(compressed_data)
        logger.debug(f"Decompression completed, decompressed size: {len(decompressed_data)} bytes")
        return decompressed_data.decode('utf-8')


# Benchmarking utility for compression and decompression performance
class CompressionBenchmark:
    def __init__(self, data: str, compressor: Compressor) -> None:
        """
        Initializes the benchmarking utility.
        
        :param data: Data to be compressed and decompressed
        :param compressor: Compressor object used for the benchmarking
        """
        self.data = data
        self.compressor = compressor

    def run_benchmark(self):
        """
        Run the compression and decompression benchmark.
        
        :return: A dictionary containing compression and decompression times
        """
        # Measure compression time
        logger.info("Starting compression benchmark")
        start_time = time.time()
        compressed_data = self.compressor.compress(self.data)
        compression_time = time.time() - start_time
        logger.info(f"Compression time: {compression_time:.4f} seconds")

        # Measure decompression time
        logger.info("Starting decompression benchmark")
        start_time = time.time()
        decompressed_data = self.compressor.decompress(compressed_data)
        decompression_time = time.time() - start_time
        logger.info(f"Decompression time: {decompression_time:.4f} seconds")

        # Verify integrity
        if decompressed_data != self.data:
            logger.error("Decompressed data does not match the original data!")
            raise ValueError("Data integrity check failed!")

        return {
            'compression_time': compression_time,
            'decompression_time': decompression_time,
            'compressed_size': len(compressed_data),
            'decompressed_size': len(decompressed_data)
        }

# Utility for logging the process and errors
class CompressionLogger:
    def __init__(self):
        """
        Initialize the logger with basic configurations.
        """
        self.logger = logging.getLogger(__name__)

    def log_error(self, message: str):
        """
        Log an error message to the console.
        
        :param message: The message to log
        """
        self.logger.error(message)

    def log_info(self, message: str):
        """
        Log an informational message to the console.
        
        :param message: The message to log
        """
        self.logger.info(message)

    def log_debug(self, message: str):
        """
        Log a debug message to the console.
        
        :param message: The message to log
        """
        self.logger.debug(message)


# Extended ZLIB with optional checksum for data integrity
class ZLIBWithChecksum(ZLIBCompressor):
    def __init__(self, compression_level: Optional[int] = 6, use_checksum: bool = False) -> None:
        """
        ZLIB compressor with optional checksum support.
        
        :param compression_level: The compression level (0-9)
        :param use_checksum: Flag to enable or disable checksum validation
        """
        super().__init__(compression_level)
        self.use_checksum = use_checksum
        logger.debug("ZLIBWithChecksum initialized with checksum: " + str(self.use_checksum))

    def compress(self, data: Union[str, bytes]) -> bytes:
        """
        Compress the data with optional checksum.
        
        :param data: Data to compress
        :return: Compressed data with checksum (if enabled)
        """
        compressed_data = super().compress(data)
        if self.use_checksum:
            checksum = zlib.crc32(compressed_data)
            logger.debug(f"Checksum for compressed data: {checksum}")
            return compressed_data + checksum.to_bytes(4, 'big')  # Append checksum to compressed data
        return compressed_data

    def decompress(self, compressed_data: bytes) -> str:
        """
        Decompress data and validate checksum (if enabled).
        
        :param compressed_data: Compressed data
        :return: Decompressed data as a string
        """
        if self.use_checksum:
            checksum = int.from_bytes(compressed_data[-4:], 'big')
            compressed_data = compressed_data[:-4]
            computed_checksum = zlib.crc32(compressed_data)
            if checksum != computed_checksum:
                raise ValueError("Checksum validation failed!")
            logger.debug(f"Checksum validated successfully: {checksum}")

        return super().decompress(compressed_data)


# Test Cases for Demonstration
def test_compression():
    original_data = "This is a test string that will be compressed and decompressed."
    logger.info("Testing ZLIB compression and decompression")

    # Initialize ZLIB compressor
    zlib_compressor = ZLIBCompressor()

    # Perform compression and decompression
    compressed_data = zlib_compressor.compress(original_data)
    decompressed_data = zlib_compressor.decompress(compressed_data)

    assert decompressed_data == original_data, "Decompression failed! Data mismatch."

    logger.info("Compression and decompression successful.")

    # Run benchmark
    benchmark = CompressionBenchmark(original_data, zlib_compressor)
    benchmark_results = benchmark.run_benchmark()
    logger.info(f"Benchmark results: {benchmark_results}")

    # Test with checksum
    logger.info("Testing ZLIB compression with checksum")
    zlib_with_checksum = ZLIBWithChecksum(use_checksum=True)
    compressed_data = zlib_with_checksum.compress(original_data)
    decompressed_data = zlib_with_checksum.decompress(compressed_data)

    assert decompressed_data == original_data, "Decompression failed with checksum!"

    logger.info("Compression and decompression with checksum successful.")
