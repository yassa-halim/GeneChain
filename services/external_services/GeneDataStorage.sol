pragma solidity ^0.8.0;

contract GeneDataStorage {
    address public owner;
    mapping(address => string) public geneData;
    mapping(address => mapping(address => bool)) public authorizedUsers;

    event GeneDataUploaded(address indexed user, string dataHash);
    event AccessGranted(address indexed owner, address indexed user);
    event AccessRevoked(address indexed owner, address indexed user);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only the owner can perform this action");
        _;
    }

    modifier onlyAuthorized(address user) {
        require(authorizedUsers[user][msg.sender] || user == msg.sender, "Not authorized to access this data");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function uploadGeneData(string memory dataHash) public {
        geneData[msg.sender] = dataHash;
        emit GeneDataUploaded(msg.sender, dataHash);
    }

    function grantAccess(address user) public onlyOwner {
        authorizedUsers[user][msg.sender] = true;
        emit AccessGranted(msg.sender, user);
    }

    function revokeAccess(address user) public onlyOwner {
        authorizedUsers[user][msg.sender] = false;
        emit AccessRevoked(msg.sender, user);
    }

    function getGeneData(address user) public view onlyAuthorized(user) returns (string memory) {
        return geneData[user];
    }
}
