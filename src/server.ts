import express, { Request, Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import pool from './config/database'; // Import MySQL pool
import saveData from './routes/save-data'; // Import save-data route

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5002;

// CORS options
const corsOptions = {
  origin: 'https://mybees.aiiot.center',
  methods: ['GET', 'POST'],
  allowedHeaders: ['Content-Type', 'Authorization'],
};

app.use(cors(corsOptions));
app.use(express.json());

// In-memory user store
const users: { username: string; password: string }[] = [
  {
    username: 'admin',
    password: 'admin123', // Plaintext password for demonstration
  },
];

// Register a new user
app.post('/api/register', async (req: Request, res: Response) => {
  const { username, password } = req.body;

  const existingUser = users.find((user) => user.username === username);
  if (existingUser) {
    return res.status(400).json({ message: 'User already exists' });
  }

  const hashedPassword = await bcrypt.hash(password, 10);
  users.push({ username, password: hashedPassword });

  res.status(201).json({ message: 'User registered successfully' });
});

// Log in and get a JWT token
app.post('/api/login', async (req: Request, res: Response) => {
  const { username, password } = req.body;

  const user = users.find((user) => user.username === username);
  if (!user) {
    return res.status(400).json({ message: 'Invalid username or password' });
  }

  const isPasswordValid = await bcrypt.compare(password, user.password);
  if (!isPasswordValid) {
    return res.status(400).json({ message: 'Invalid username or password' });
  }

  const token = jwt.sign({ username: user.username }, process.env.JWT_SECRET || 'your-secret-key', {
    expiresIn: '1h',
  });
  res.status(200).json({ token });
});

// Fetch data from the database
app.get('/api/data', async (req: Request, res: Response) => {
  const query = 'SELECT * FROM sensor_data';

  try {
    const [results] = await pool.query(query);
    res.json(results);
  } catch (err: any) {
    console.error('Database query error:', err.message);
    res.status(500).json({ message: 'Database query error', error: err.message });
  }
});

// Use the save-data route
app.use('/save-data', saveData);

// Start the server
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
