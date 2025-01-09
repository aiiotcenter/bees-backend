const db = require('../config/db');

// @desc Register a new user
// @route POST /api/users
const registerUser = (req, res) => {
  const { name, email, password } = req.body;

  const checkEmail = 'SELECT * FROM users WHERE email = ?';
  const insertUser = 'INSERT INTO users (name, email, password) VALUES (?, ?, ?)';

  // Check if email already exists
  db.query(checkEmail, [email], (err, results) => {
    if (results.length > 0) {
      return res.status(400).json({ message: 'User already exists' });
    } else {
      // Insert new user
      db.query(insertUser, [name, email, password], (err, result) => {
        if (err) {
          console.error(err);
          return res.status(500).json({ message: 'Server error' });
        }
        res.status(201).json({ id: result.insertId, name, email });
      });
    }
  });
};

module.exports = { registerUser };
