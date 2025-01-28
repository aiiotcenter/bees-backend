"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const dotenv_1 = __importDefault(require("dotenv"));
const bcryptjs_1 = __importDefault(require("bcryptjs"));
const jsonwebtoken_1 = __importDefault(require("jsonwebtoken"));
const cors_1 = __importDefault(require("cors")); // Import cors
const database_1 = __importDefault(require("./config/database")); // Import MySQL pool
const save_data_1 = __importDefault(require("./routes/save-data")); // Import save-data route
dotenv_1.default.config();
const app = (0, express_1.default)();
const PORT = process.env.PORT || 5002;
// Enable CORS for all origins
app.use((0, cors_1.default)());
app.use(express_1.default.json());
// In-memory user store
const users = [
    {
        username: 'admin',
        password: 'admin123', // Plaintext password for demonstration
    },
];
// Register a new user
app.post('/api/register', (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    const { username, password } = req.body;
    const existingUser = users.find((user) => user.username === username);
    if (existingUser) {
        return res.status(400).json({ message: 'User already exists' });
    }
    const hashedPassword = yield bcryptjs_1.default.hash(password, 10);
    users.push({ username, password: hashedPassword });
    res.status(201).json({ message: 'User registered successfully' });
}));
// Log in and get a JWT token
app.post('/api/login', (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    const { username, password } = req.body;
    const user = users.find((user) => user.username === username);
    if (!user) {
        return res.status(400).json({ message: 'Invalid username or password' });
    }
    const isPasswordValid = yield bcryptjs_1.default.compare(password, user.password);
    if (!isPasswordValid) {
        return res.status(400).json({ message: 'Invalid username or password' });
    }
    const token = jsonwebtoken_1.default.sign({ username: user.username }, process.env.JWT_SECRET || 'your-secret-key', {
        expiresIn: '1h',
    });
    res.status(200).json({ token });
}));
// Fetch data from the database
app.get('/api/data', (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    const query = 'SELECT * FROM sensor_data';
    try {
        const [results] = yield database_1.default.query(query);
        res.json(results);
    }
    catch (err) {
        console.error('Database query error:', err.message);
        res.status(500).json({ message: 'Database query error', error: err.message });
    }
}));
// Use the save-data route
app.use('/save-data', save_data_1.default);
// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
