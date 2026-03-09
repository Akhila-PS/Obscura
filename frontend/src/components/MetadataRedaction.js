// src/components/MetadataRedaction.js
import React, { useState } from "react";
import {
  Container,
  Box,
  Button,
  Typography,
  CircularProgress,
  Alert,
  List,
  ListItem,
  Paper,
  IconButton,
} from "@mui/material";
import { motion } from "framer-motion";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useNavigate } from "react-router-dom";
import axios from "axios";

export default function MetadataRedaction() {
  const navigate = useNavigate();

  const [file, setFile] = useState(null);
  const [originalPreview, setOriginalPreview] = useState(null);
  const [metadata, setMetadata] = useState({});
  const [riskScore, setRiskScore] = useState(null);
  const [explanations, setExplanations] = useState([]);
  const [strippedImage, setStrippedImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasAnalyzed, setHasAnalyzed] = useState(false);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setOriginalPreview(URL.createObjectURL(selectedFile));
      setStrippedImage(null);
      setMetadata({});
      setRiskScore(null);
      setExplanations([]);
      setHasAnalyzed(false);
    }
  };

  const handleExtract = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setHasAnalyzed(false);

    const formData = new FormData();
    formData.append("image", file);

    try {
      const res = await axios.post("/metadata", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 60000,
      });
      setMetadata(res.data.metadata || {});
      setRiskScore(res.data.risk_score || 0);
      setExplanations(res.data.explanations || []);
      setHasAnalyzed(true);
    } catch (err) {
      setError("Failed to extract metadata. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStrip = async () => {
    if (!file) return;
    setLoading(true);

    const formData = new FormData();
    formData.append("image", file);

    try {
      const res = await axios.post("/strip-metadata", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 60000,
      });
      setStrippedImage(`data:image/png;base64,${res.data.redacted_image}`);
    } catch (err) {
      setError("Failed to strip metadata.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (strippedImage) {
      const link = document.createElement("a");
      link.href = strippedImage;
      link.download = "metadata_stripped.png";
      link.click();
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 10, position: "relative" }}>
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

      {/* Subtle background */}
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          background: "radial-gradient(circle at 30% 70%, rgba(96,165,250,0.08) 0%, transparent 70%)",
          zIndex: -1,
        }}
      />

      {/* Title */}
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
            background: "linear-gradient(90deg, #60A5FA 0%, #3B82F6 50%, #2563EB 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            mb: 2,
            textShadow: "0 6px 24px rgba(59,130,246,0.3)",
          }}
        >
          Metadata Redaction
        </Typography>

        <Typography variant="h6" align="center" color="text.secondary" sx={{ mb: 8 }}>
          Remove hidden traces • Protect your privacy footprint
        </Typography>
      </motion.div>

      {/* Upload Section */}
      <Box sx={{ textAlign: "center", mb: 6 }}>
        <input
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          style={{ display: "none" }}
          id="metadata-upload"
        />
        <label htmlFor="metadata-upload">
          <Button
            variant="contained"
            component="span"
            startIcon={<CloudUploadIcon />}
            size="large"
            sx={{ py: 2, px: 5 }}
          >
            Choose Image
          </Button>
        </label>

        {file && (
          <Button
            variant="outlined"
            onClick={handleExtract}
            sx={{ ml: 3, py: 2, px: 5 }}
          >
            Analyze Metadata
          </Button>
        )}
      </Box>

      {/* Preview */}
      {file && originalPreview && (
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Paper elevation={6} sx={{ p: 3, mt: 4, borderRadius: 4, textAlign: "center" }}>
            <Typography variant="subtitle1" gutterBottom>
              Selected Image
            </Typography>
            <img
              src={originalPreview}
              alt="Preview"
              style={{
                maxWidth: "100%",
                maxHeight: "450px",
                borderRadius: 12,
                boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
              }}
            />
          </Paper>
        </motion.div>
      )}

      {loading && (
        <Box sx={{ textAlign: 'center', my: 8 }}>
          <CircularProgress size={50} thickness={5} />
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mt: 5, maxWidth: 700, mx: "auto" }}>{error}</Alert>}

      {hasAnalyzed && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          {Object.keys(metadata).length > 0 ? (
            <Paper
              elevation={8}
              sx={{
                p: 5,
                mt: 6,
                borderRadius: 4,
                background: "linear-gradient(145deg, rgba(30,41,59,0.92) 0%, rgba(15,23,42,0.98) 100%)",
                border: "1px solid rgba(96,165,250,0.2)",
                backdropFilter: "blur(10px)",
              }}
            >
              <Typography variant="h5" gutterBottom sx={{ fontWeight: 700, color: "#60A5FA" }}>
                Extracted Metadata
              </Typography>
              <List dense>
                {Object.entries(metadata).map(([key, value]) => (
                  <ListItem key={key} sx={{ py: 1 }}>
                    <strong style={{ minWidth: 180, color: "#e2e8f0" }}>{key}:</strong>
                    <span style={{ color: "#94a3b8" }}>{value}</span>
                  </ListItem>
                ))}
              </List>

              <Typography variant="h5" sx={{ mt: 5, mb: 1, fontWeight: 700 }}>
                Risk Assessment
              </Typography>
              <Typography
                variant="h4"
                sx={{
                  fontWeight: "bold",
                  color: riskScore > 50 ? "#ef4444" : riskScore > 0 ? "#f59e0b" : "#22c55e",
                }}
              >
                {riskScore} {riskScore > 50 ? "(High Risk)" : riskScore > 0 ? "(Medium Risk)" : "(Low Risk)"}
              </Typography>

              {explanations.length > 0 && (
                <>
                  <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>
                    Sensitive Items Detected
                  </Typography>
                  <List dense>
                    {explanations.map((exp, i) => (
                      <ListItem key={i} sx={{ color: "#94a3b8" }}>• {exp}</ListItem>
                    ))}
                  </List>
                </>
              )}

              <Button
                variant="contained"
                fullWidth
                sx={{
                  mt: 5,
                  py: 2,
                  background: "linear-gradient(90deg, #3B82F6, #2563EB)",
                  "&:hover": { background: "linear-gradient(90deg, #60A5FA, #3B82F6)" },
                }}
                onClick={handleStrip}
              >
                Strip All Metadata
              </Button>
            </Paper>
          ) : (
            <Paper
              elevation={8}
              sx={{
                p: 6,
                mt: 6,
                borderRadius: 4,
                textAlign: "center",
                background: "linear-gradient(145deg, rgba(30,41,59,0.92) 0%, rgba(15,23,42,0.98) 100%)",
                border: "1px solid rgba(34,197,94,0.3)",
                backdropFilter: "blur(12px)",
              }}
            >
              <CheckCircleOutlineIcon sx={{ fontSize: 80, color: "#22c55e", mb: 3 }} />
              <Typography variant="h4" gutterBottom sx={{ fontWeight: 700, color: "#22c55e" }}>
                Safe & Clean!
              </Typography>
              <Typography variant="h6" sx={{ mb: 3, color: "#94a3b8" }}>
                No metadata or traces detected
              </Typography>
              <Typography variant="h3" sx={{ fontWeight: "bold", color: "#22c55e" }}>
                Risk Score: 0
              </Typography>
              <Typography variant="body1" sx={{ mt: 3, fontSize: "1.15rem", color: "#cbd5e1" }}>
                This image is already fully protected — no location, device, or sensitive data remains.
              </Typography>
            </Paper>
          )}
        </motion.div>
      )}

      {strippedImage && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Paper
            elevation={8}
            sx={{
              p: 5,
              mt: 8,
              borderRadius: 4,
              background: "linear-gradient(145deg, rgba(30,41,59,0.92) 0%, rgba(15,23,42,0.98) 100%)",
              border: "1px solid rgba(34,197,94,0.3)",
              backdropFilter: "blur(10px)",
            }}
          >
            <Typography variant="h5" gutterBottom sx={{ fontWeight: 700, color: "#22c55e" }}>
              Clean Image Ready
            </Typography>
            <Box sx={{ textAlign: "center", my: 4 }}>
              <img
                src={strippedImage}
                alt="Clean"
                style={{
                  maxWidth: "100%",
                  maxHeight: "500px",
                  borderRadius: 16,
                  boxShadow: "0 10px 40px rgba(0,0,0,0.4)",
                }}
              />
            </Box>
            <Button
              variant="contained"
              fullWidth
              sx={{
                py: 2,
                background: "linear-gradient(90deg, #22c55e, #16a34a)",
                "&:hover": { background: "linear-gradient(90deg, #16a34a, #22c55e)" },
              }}
              onClick={handleDownload}
            >
              Download Protected Image
            </Button>
            <Typography variant="body2" align="center" sx={{ mt: 3, color: "text.secondary" }}>
              Re-upload to verify: zero risk, zero metadata.
            </Typography>
          </Paper>
        </motion.div>
      )}
    </Container>
  );
}