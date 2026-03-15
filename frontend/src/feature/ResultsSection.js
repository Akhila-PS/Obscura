// src/components/ResultsSection.js
// FIXED VERSION - Shows redacted output correctly for both images and PDFs

import React from "react";
import { Box, Typography, Button, Paper } from "@mui/material";
import { motion } from "framer-motion";
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';

function ResultsSection({ originalFile, redactedOutput, outputType, riskScore, explanations, aiSummary }) {

  return (
    <Box sx={{ mt: 6 }}>
      <Typography variant="h4" sx={{ mb: 3, textAlign: 'center', fontWeight: 700 }}>
        Privacy Protection Results
      </Typography>

      {/* AI Summary Section */}
      {
        aiSummary && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <Paper
              elevation={4}
              sx={{
                p: 3,
                mb: 4,
                borderRadius: 3,
                background: 'linear-gradient(135deg, rgba(59,130,246,0.1) 0%, rgba(147,51,234,0.1) 100%)',
                border: '1px solid',
                borderColor: 'primary.light'
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <AutoAwesomeIcon sx={{ color: 'primary.main', mr: 1 }} />
                <Typography variant="h6" sx={{ fontWeight: 600, color: 'primary.main' }}>
                  AI Redaction Summary
                </Typography>
              </Box>
              <Typography variant="body1" sx={{ lineHeight: 1.6 }}>
                {aiSummary}
              </Typography>
            </Paper>
          </motion.div>
        )
      }

      {/* Risk Score */}
      <Box sx={{ textAlign: 'center', mb: 4 }}>
        <Typography variant="h6">
          Risk Score: <span style={{
            color: riskScore > 60 ? '#ef4444' : riskScore > 30 ? '#f59e0b' : '#22c55e',
            fontWeight: 'bold'
          }}>
            {riskScore}/100
          </span>
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {riskScore > 60 ? 'High Risk - Multiple sensitive items detected' :
            riskScore > 30 ? 'Medium Risk - Some sensitive items detected' :
              'Low Risk - Minimal sensitive data'}
        </Typography>
      </Box>

      {/* Before/After Comparison */}
      <Box sx={{
        display: 'flex',
        flexDirection: { xs: 'column', md: 'row' },
        gap: 3,
        justifyContent: 'center',
        mb: 4
      }}>

        {/* ORIGINAL FILE */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          style={{ flex: 1, maxWidth: '45%' }}
        >
          <Paper elevation={6} sx={{ p: 2, borderRadius: 3 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
              📄 Original File
            </Typography>

            {outputType === 'pdf' ? (
              <iframe
                src={originalFile + "#zoom=page-fit&toolbar=0"}
                width="100%"
                height="600px"
                style={{ border: '1px solid #ccc', borderRadius: '8px', display: 'block' }}
                title="Original PDF"
              />
            ) : (
              <img
                src={originalFile}
                alt="Original"
                style={{
                  width: '100%',
                  borderRadius: '8px',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.15)'
                }}
              />
            )}
          </Paper>
        </motion.div>

        {/* REDACTED FILE */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          style={{ flex: 1, maxWidth: '45%' }}
        >
          <Paper
            elevation={6}
            sx={{
              p: 2,
              borderRadius: 3,
              border: '2px solid',
              borderColor: 'success.main'
            }}
          >
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: 'success.main' }}>
              ✅ Redacted & Protected
            </Typography>

            {outputType === 'pdf' ? (
              <iframe
                src={redactedOutput + "#zoom=page-fit&toolbar=0"}
                width="100%"
                height="600px"
                style={{ border: '1px solid #ccc', borderRadius: '8px', display: 'block' }}
                title="Redacted PDF"
              />
            ) : (
              <img
                src={redactedOutput}
                alt="Redacted"
                style={{
                  width: '100%',
                  borderRadius: '8px',
                  boxShadow: '0 4px 20px rgba(34,197,94,0.2)'
                }}
              />
            )}
          </Paper>
        </motion.div>

      </Box>

      {/* Download Button */}
      <Box sx={{ textAlign: 'center', mt: 4 }}>
        <Button
          variant="contained"
          color="success"
          href={redactedOutput}
          download={`redacted_${Date.now()}.${outputType === 'pdf' ? 'pdf' : 'png'}`}
          size="large"
          sx={{
            py: 2,
            px: 6,
            fontSize: '1.1rem',
            fontWeight: 600
          }}
        >
          Download Redacted File
        </Button>
      </Box>

      {/* Explanations */}
      {
        explanations && explanations.length > 0 && (
          <Box sx={{ mt: 6 }}>
            <Paper elevation={4} sx={{ p: 4, borderRadius: 3 }}>
              <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                🔒 Redactions Applied ({explanations.length}):
              </Typography>
              <Box component="ul" sx={{ pl: 3, m: 0 }}>
                {explanations.map((exp, idx) => (
                  <li key={idx} style={{ marginBottom: '8px' }}>
                    <Typography variant="body1">{exp}</Typography>
                  </li>
                ))}
              </Box>
            </Paper>
          </Box>
        )
      }
    </Box>
  );
}

export default ResultsSection;