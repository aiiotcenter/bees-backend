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
const fs_1 = __importDefault(require("fs"));
const database_1 = __importDefault(require("../config/database"));
const router = express_1.default.Router();
router.post('/', (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    const { temperature = 0.0, humidity = 0.0, weight = 0.0, distance = 0.0, sound_status = 0, light_status = 0, } = req.body;
    // Log received data for debugging
    const logData = `Received Data: Temp=${temperature}, Hum=${humidity}, Weight=${weight}, Dist=${distance}, Sound=${sound_status}, Light=${light_status}\n`;
    fs_1.default.appendFileSync('debug.log', logData);
    try {
        const sql = "INSERT INTO sensor_data (temperature, humidity, weight, distance, sound_status, light_status) VALUES (?, ?, ?, ?, ?, ?)";
        yield database_1.default.query(sql, [temperature, humidity, weight, distance, sound_status, light_status]);
        res.status(201).json({ status: "success", message: "Data saved successfully." });
    }
    catch (err) {
        fs_1.default.appendFileSync('debug.log', `Database Error: ${err.message}\n`);
        res.status(500).json({ status: "error", message: "Failed to save data." });
    }
}));
exports.default = router;
