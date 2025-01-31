import express, { Request, Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import pool from './config/database'; // Import MySQL pool
import saveData from './routes/save-data'; // Import save-data route

dotenv.config();
const app = express();
const PORT = process.env.PORT || 5002;

// CORS options
const corsOptions = {
  origin: 'http://mybees.aiiot.center/dashboard',
  methods: ['GET', 'POST'],
  allowedHeaders: ['Content-Type', 'Authorization'],
};

app.use(cors(corsOptions));
app.use(express.json());

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
