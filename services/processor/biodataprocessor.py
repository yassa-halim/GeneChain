import json
import re
from typing import Dict, Any

class BioDataProcessor:
    def __init__(self):
        self.data_format = "json"

    def parse_data(self, raw_data: str) -> Dict[str, Any]:
        try:
            data = json.loads(raw_data)
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

    def validate_data(self, data: Dict[str, Any]) -> bool:
        required_fields = ["gene_id", "sequence", "metadata"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        sequence = data.get("sequence", "")
        if not re.match("^[ACGT]+$", sequence):
            raise ValueError("Invalid gene sequence format")
        
        return True

    def preprocess_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data["sequence"] = data["sequence"].upper()
        return data

    def format_data(self, data: Dict[str, Any]) -> str:
        if self.data_format == "json":
            return json.dumps(data)
        else:
            raise NotImplementedError(f"Format '{self.data_format}' not supported")

    def process_raw_data(self, raw_data: str) -> str:
        data = self.parse_data(raw_data)
        if self.validate_data(data):
            data = self.preprocess_data(data)
        return self.format_data(data)

class BioDataParser:
    def __init__(self):
        pass

    def parse_from_file(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, 'r') as file:
            data = file.read()
        return self.parse_data(data)

    def parse_data(self, raw_data: str) -> Dict[str, Any]:
        try:
            data = json.loads(raw_data)
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

    def extract_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if 'metadata' in data:
            return data['metadata']
        else:
            raise ValueError("Metadata not found in the data")

class BioDataValidator:
    def __init__(self):
        pass

    def validate(self, data: Dict[str, Any]) -> bool:
        required_fields = ["gene_id", "sequence", "metadata"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        sequence = data.get("sequence", "")
        if not re.match("^[ACGT]+$", sequence):
            raise ValueError("Invalid gene sequence format")

        return True

class BioDataSerializer:
    def __init__(self, data_format="json"):
        self.data_format = data_format

    def serialize(self, data: Dict[str, Any]) -> str:
        if self.data_format == "json":
            return json.dumps(data)
        else:
            raise NotImplementedError(f"Format '{self.data_format}' not supported")

    def deserialize(self, raw_data: str) -> Dict[str, Any]:
        try:
            return json.loads(raw_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
