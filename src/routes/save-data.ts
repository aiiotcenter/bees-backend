import express, { Request, Response } from 'express';
import fs from 'fs';
import pool from '../config/database';

const router = express.Router();

router.post('/', async (req: Request, res: Response) => {
  const {
    temperature = 0.0,
    humidity = 0.0,
    weight = 0.0,
    distance = 0.0,
    sound_status = 0,
    light_status = 0,
  } = req.body;

  // Log received data for debugging
  const logData = `Received Data: Temp=${temperature}, Hum=${humidity}, Weight=${weight}, Dist=${distance}, Sound=${sound_status}, Light=${light_status}\n`;
  fs.appendFileSync('debug.log', logData);

  try {
    const sql =
      "INSERT INTO sensor_data (temperature, humidity, weight, distance, sound_status, light_status) VALUES (?, ?, ?, ?, ?, ?)";
    await pool.query(sql, [temperature, humidity, weight, distance, sound_status, light_status]);

    res.status(201).json({ status: "success", message: "Data saved successfully." });
  } catch (err: any) {
    fs.appendFileSync('debug.log', `Database Error: ${err.message}\n`);
    res.status(500).json({ status: "error", message: "Failed to save data." });
  }
});

export default router;
