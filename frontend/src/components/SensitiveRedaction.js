// src/components/SensitiveRedaction.js
import React, { useState } from "react";
import {
  Container,
  Typography,
  Box,
  IconButton,
  CircularProgress,
  Alert,
  Divider,
  Tooltip,
  FormControlLabel,
  Checkbox,
  Paper,
  Button,
  TextField,
} from "@mui/material";
import { motion } from "framer-motion";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useNavigate } from "react-router-dom";

import UploadSection from "../feature/UploadSection";
import ResultsSection from "../feature/ResultsSection";
import axios from "axios";

function SensitiveRedaction({ mode, toggleColorMode }) {
  const navigate = useNavigate();

  const [originalFile, setOriginalFile] = useState(null);
  const [redactedOutput, setRedactedOutput] = useState(null);
  const [outputType, setOutputType] = useState(null);
  const [riskScore, setRiskScore] = useState(null);
  const [explanations, setExplanations] = useState([]);
  const [aiSummary, setAiSummary] = useState(null);
  const [customPrompt, setCustomPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasProcessed, setHasProcessed] = useState(false);

  const [redactionOptions, setRedactionOptions] = useState({
    general_pii: true,
    aadhaar: true,
    vid: true,
    phone: true,
    qr: true,
    face: false,
    email: false,
    plate: false,
    partial: true,
    watermark: true,
  });

  const handleOptionChange = (key) => {
    setRedactionOptions((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };
  const API = process.env.REACT_APP_API_URL || "http://localhost:5000";
  const handleUpload = async (file) => {
    if (!file) {
      setError("No file selected.");
      return;
    }

    // Already-redacted file — show safe immediately, skip backend
    if (file.name.toLowerCase().startsWith("redacted_")) {
      setOriginalFile(URL.createObjectURL(file));
      setExplanations([]);
      setRiskScore(0);
      setAiSummary("This file has already been redacted by Obscura. No sensitive data detected.");
      setOutputType(null);
      setRedactedOutput(null);
      setHasProcessed(true);
      return;
    }

    setLoading(true);
    setError(null);
    setHasProcessed(false);
    setOriginalFile(URL.createObjectURL(file));

    const formData = new FormData();
    formData.append("image", file);
    formData.append("options", JSON.stringify(redactionOptions));
    formData.append("custom_prompt", customPrompt);

    try {
      const isPdf = file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf";
      const res = await axios.post("${API}/upload", formData, {
        timeout: isPdf ? 600000 : 180000,
      });

      setOutputType(res.data.type);
      setRiskScore(res.data.risk_score);
      setExplanations(res.data.explanations || []);
      setAiSummary(res.data.ai_summary || null);
      setHasProcessed(true);

      if (res.data.already_clean) {
        setRedactedOutput(null);
        return;
      }

      if (res.data.type === "image") {
        setRedactedOutput(`data:image/png;base64,${res.data.redacted_image}`);
      }

      if (res.data.type === "pdf") {
        const binary = atob(res.data.redacted_pdf);
        const bytes = new Uint8Array([...binary].map((c) => c.charCodeAt(0)));
        const blob = new Blob([bytes], { type: "application/pdf" });
        setRedactedOutput(URL.createObjectURL(blob));
      }
    } catch (err) {
      console.error("Upload error:", err);
      const errorMessage =
        err?.response?.data?.error ||
        err?.message ||
        "Failed to process file. Please try again.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: { xs: 4, md: 8 }, position: 'relative' }}>
      {/* Back Button */}
      <IconButton
        onClick={() => navigate("/")}
        sx={{
          position: 'absolute',
          top: 24,
          left: 24,
          color: 'text.secondary',
          '&:hover': { color: 'primary.main' },
        }}
      >
        <ArrowBackIcon />
      </IconButton>

      {/* Theme Toggle */}
      <Tooltip title={`Switch to ${mode === 'dark' ? 'light' : 'dark'} mode`}>
        <IconButton
          onClick={toggleColorMode}
          sx={{
            position: 'absolute',
            top: 24,
            right: 24,
            color: 'text.secondary',
            '&:hover': { color: 'primary.main' },
          }}
        >
          {mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
        </IconButton>
      </Tooltip>

      {/* Hero Title */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
      >
        <Typography
          variant="h3"
          align="center"
          sx={{
            fontWeight: 900,
            background: 'linear-gradient(90deg, #60A5FA 0%, #3B82F6 50%, #2563EB 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            mb: 2,
            textShadow: '0 6px 24px rgba(59,130,246,0.3)',
          }}
        >
          Sensitive Information Redaction
        </Typography>

        <Typography
          variant="subtitle1"
          align="center"
          color="text.secondary"
          sx={{ mb: 6, fontSize: '1.1rem' }}
        >
          Auto-detect & obscure Aadhaar, phones, emails, QR codes & more
        </Typography>
      </motion.div>

      {/* Redaction Options */}
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, delay: 0.1 }}
      >
        <Paper
          elevation={6}
          sx={{
            p: 4,
            mb: 4,
            borderRadius: 4,
            background: mode === 'dark'
              ? 'linear-gradient(145deg, rgba(30,41,59,0.92) 0%, rgba(15,23,42,0.98) 100%)'
              : 'rgba(255,255,255,0.95)',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
            🎯 Customize Redaction Options
          </Typography>

          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.general_pii}
                  onChange={() => handleOptionChange('general_pii')}
                  color="primary"
                />
              }
              label="General PII (IDs, DOBs, Expiry, etc)"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.aadhaar}
                  onChange={() => handleOptionChange('aadhaar')}
                  color="primary"
                />
              }
              label="Aadhaar Numbers"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.vid}
                  onChange={() => handleOptionChange('vid')}
                  color="primary"
                />
              }
              label="VID Numbers (16 digits)"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.phone}
                  onChange={() => handleOptionChange('phone')}
                  color="primary"
                />
              }
              label="Phone Numbers"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.qr}
                  onChange={() => handleOptionChange('qr')}
                  color="primary"
                />
              }
              label="QR Codes"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.face}
                  onChange={() => handleOptionChange('face')}
                  color="secondary"
                />
              }
              label="Faces (Blur)"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.email}
                  onChange={() => handleOptionChange('email')}
                  color="secondary"
                />
              }
              label="Email Addresses"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.plate}
                  onChange={() => handleOptionChange('plate')}
                  color="secondary"
                />
              }
              label="License Plates"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.partial}
                  onChange={() => handleOptionChange('partial')}
                  color="primary"
                />
              }
              label="Partial Redaction (show last 4)"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.watermark}
                  onChange={() => handleOptionChange('watermark')}
                  color="primary"
                />
              }
              label="Add Watermark"
            />
          </Box>
        </Paper>
      </motion.div>

      {/* Smart Redaction Custom Rule */}
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, delay: 0.15 }}
      >
        <Paper
          elevation={6}
          sx={{
            p: 4,
            mb: 4,
            borderRadius: 4,
            background: mode === 'dark'
              ? 'linear-gradient(145deg, rgba(30,41,59,0.92) 0%, rgba(15,23,42,0.98) 100%)'
              : 'rgba(255,255,255,0.95)',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
            🤖 Smart AI Redaction (Optional)
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Use natural language to specify what else you want to redact (e.g., "Redact the patient's full name and address" or "Hide all mentions of Project Titan").
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={2}
            variant="outlined"
            placeholder="Type your custom redaction rule here..."
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
          />
        </Paper>
      </motion.div>

      {/* Upload Card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        <Box
          sx={{
            bgcolor: 'background.paper',
            borderRadius: 4,
            p: { xs: 4, md: 5 },
            boxShadow: mode === 'dark'
              ? '0 15px 35px rgba(0,0,0,0.5)'
              : '0 15px 35px rgba(0,0,0,0.1)',
            border: '1px solid',
            borderColor: 'divider',
            textAlign: 'center',
            maxWidth: '480px',
            mx: 'auto',
          }}
        >
          <CloudUploadIcon sx={{ fontSize: 80, color: 'primary.main', mb: 2 }} />

          <UploadSection onUpload={handleUpload} />

          {loading && (
            <Box mt={4}>
              <CircularProgress size={50} thickness={5} />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Processing your file…
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1, fontSize: '0.75rem', opacity: 0.7 }}>
                PDFs may take a minute per page
              </Typography>
            </Box>
          )}
        </Box>
      </motion.div>

      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <Alert severity="error" sx={{ mt: 4, borderRadius: 3 }}>
            {error}
          </Alert>
        </motion.div>
      )}

      {hasProcessed && explanations.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
        >
          <Divider sx={{ my: 8, borderColor: 'divider' }} />
          <Paper
            elevation={8}
            sx={{
              p: 6,
              borderRadius: 4,
              textAlign: 'center',
              background: mode === 'dark'
                ? 'linear-gradient(145deg, rgba(30,41,59,0.92) 0%, rgba(15,23,42,0.98) 100%)'
                : 'rgba(255,255,255,0.95)',
              border: '1px solid rgba(34,197,94,0.3)',
              backdropFilter: 'blur(12px)',
            }}
          >
            <CheckCircleOutlineIcon sx={{ fontSize: 80, color: '#22c55e', mb: 3 }} />
            <Typography variant="h4" gutterBottom sx={{ fontWeight: 700, color: '#22c55e' }}>
              No Sensitive Data Found
            </Typography>
            <Typography variant="h6" sx={{ mb: 2, color: '#94a3b8' }}>
              This document is safe
            </Typography>
            <Typography variant="body1" sx={{ color: '#cbd5e1', fontSize: '1.05rem' }}>
              {aiSummary || "No redaction needed — no Aadhaar, phone numbers, QR codes, or other sensitive information was detected."}
            </Typography>
          </Paper>
        </motion.div>
      )}

      {hasProcessed && explanations.length > 0 && redactedOutput && (
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
        >
          <Divider sx={{ my: 8, borderColor: 'divider' }} />

          <ResultsSection
            originalFile={originalFile}
            redactedOutput={redactedOutput}
            outputType={outputType}
            riskScore={riskScore}
            explanations={explanations}
            aiSummary={aiSummary}
          />
        </motion.div>
      )}
    </Container>
  );
}

export default SensitiveRedaction;