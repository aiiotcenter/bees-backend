// Import required modules
const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const pool = require('./config/database'); // Import the database configuration

// Create an Express application
const app = express();

// Middleware to parse JSON body
app.use(bodyParser.json());

// Endpoint to handle POST requests
app.post('/save-data', (req, res) => {
  const {
    temperature = 0.0,
    humidity = 0.0,
    weight = 0.0,
    distance = 0.0,
    sound_status = 0,
    light_status = 0
  } = req.body;

  // Log received data for debugging
  const logData = `Received Data: Temp=${temperature}, Hum=${humidity}, Weight=${weight}, Dist=${distance}, Sound=${sound_status}, Light=${light_status}\n`;
  fs.appendFileSync('debug.log', logData);

  // SQL query to insert data into the database
  const sql = "INSERT INTO sensor_data (temperature, humidity, weight, distance, sound_status, light_status) VALUES (?, ?, ?, ?, ?, ?)";

  pool.execute(sql, [temperature, humidity, weight, distance, sound_status, light_status], (err, results) => {
    if (err) {
      fs.appendFileSync('debug.log', `Database Error: ${err.message}\n`);
      return res.status(500).json({ status: "error", message: "Failed to save data." });
    }

    res.json({ status: "success", message: "Data saved successfully." });
  });
});

// Start the server
const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
