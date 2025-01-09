const express = require('express');
const cors = require('cors');
const db = require('./config/database');
const jwt = require('jsonwebtoken');
const fs = require('fs');
const bcrypt = require('bcryptjs');
const dotenv = require('dotenv');
const saveData = require('./save-data'); // Import save-data.js
dotenv.config();

const app = express();

const PORT = process.env.PORT || 5002;

const corsOptions = {
  origin: 'https://bees.aiiot.center', // Replace with the allowed origin
  methods: ['GET', 'POST'], // Specify allowed HTTP methods
  allowedHeaders: ['Content-Type', 'Authorization'], // Specify allowed headers
};

app.use(cors());
app.use(express.json());


// In-memory user store (simulating a database for this example)
let users = [
  {
    username: 'admin',
    password: 'admin123' // 'password123' hashed
  }
];

// Middleware to protect routes that require authentication
const authenticateJWT = (req, res, next) => {
  const token = req.header('Authorization')?.split(' ')[1]; // Bearer <token>
  if (!token) {
    return res.status(403).json({ message: 'Access denied. No token provided.' });
  }

  jwt.verify(token, JWT_SECRET, (err, user) => {
    if (err) {
      return res.status(403).json({ message: 'Invalid token' });
    }
    req.user = user;
    next();
  });
};


// Route to register a new user (For simplicity, we'll skip database and add static users)
app.post('/api/register', async (req, res) => {
  const { username, password } = req.body;

  // Check if the user already exists
  const existingUser = users.find(user => user.username === username);
  if (existingUser) {
    return res.status(400).json({ message: 'User already exists' });
  }

  // Hash the password
  const hashedPassword = await bcrypt.hash(password, 10);

  // Add the new user to the user array
  users.push({ username, password: hashedPassword });

  return res.status(201).json({ message: 'User registered successfully' });
});

// Route to log in and get a JWT token
app.post('/api/login', async (req, res) => {
  const { username, password } = req.body;

  // Check if the user exists
  const user = users.find(user => user.username === username);
  if (!user) {
    return res.status(400).json({ message: 'Invalid username or password' });
  }

  // Check if the password is correct
  const isPasswordValid = await bcrypt.compare(password, user.password);
  if (!isPasswordValid) {
    return res.status(400).json({ message: 'Invalid username or password' });
  }

  // Generate a JWT token
  const token = jwt.sign({ username: user.username }, JWT_SECRET, { expiresIn: '1h' });

  return res.status(200).json({ token });
});

// Protected route to fetch data from the database
app.get('/api/data', authenticateJWT, (req, res) => {
  const query = 'SELECT * FROM sensor_data';  // Make sure this query is correct

  db.query(query, (err, results) => {
    if (err) {
      console.error('Database query error:', err);
      return res.status(500).json({ message: 'Database query error', error: err.message });
    }
    console.log('Fetched data:', results);
    res.json(results);
  });
});

// Use the save-data route
app.use('/save-data', saveData);

app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});