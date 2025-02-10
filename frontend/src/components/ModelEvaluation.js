import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  IconButton,
  Typography,
  CircularProgress,
} from '@mui/material';
import ArrowBack from '@mui/icons-material/ArrowBack';
import ArrowForward from '@mui/icons-material/ArrowForward';
import axios from 'axios';

const ModelEvaluation = () => {
  const [charts, setCharts] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCharts = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/model-evaluation`);
        setCharts(response.data);
        setLoading(false);
      } catch (err) {
        setError('Failed to load model evaluation data');
        setLoading(false);
      }
    };
    fetchCharts();
  }, []);

  const handleNext = () => {
    setCurrentIndex((prevIndex) => 
      prevIndex === charts.length - 1 ? 0 : prevIndex + 1
    );
  };

  const handlePrevious = () => {
    setCurrentIndex((prevIndex) => 
      prevIndex === 0 ? charts.length - 1 : prevIndex - 1
    );
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  if (!charts.length) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>No evaluation charts available</Typography>
      </Box>
    );
  }

  const currentChart = charts[currentIndex];

  return (
    <Paper elevation={3} sx={{ p: 3, my: 2 }}>
      <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
        <Typography variant="h6" gutterBottom>
          Model Evaluation Charts
        </Typography>
        
        <Box display="flex" alignItems="center" width="100%" justifyContent="space-between">
          <IconButton onClick={handlePrevious}>
            <ArrowBack />
          </IconButton>
          
          <Box 
            sx={{ 
              flex: 1, 
              mx: 2, 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center' 
            }}
          >
            <img 
              src={`data:image/png;base64,${currentChart.image}`}
              alt={currentChart.title}
              style={{ maxWidth: '100%', height: 'auto', maxHeight: '400px' }}
            />
            <Typography variant="h6" sx={{ mt: 2 }}>
              {currentChart.title}
            </Typography>
            <Typography variant="body1" sx={{ mt: 1, textAlign: 'center' }}>
              {currentChart.description}
            </Typography>
          </Box>

          <IconButton onClick={handleNext}>
            <ArrowForward />
          </IconButton>
        </Box>

        <Typography variant="body2" color="text.secondary">
          Chart {currentIndex + 1} of {charts.length}
        </Typography>
      </Box>
    </Paper>
  );
};

export default ModelEvaluation;
