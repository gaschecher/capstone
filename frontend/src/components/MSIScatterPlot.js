import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Chart as ChartJS,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Scatter } from 'react-chartjs-2';
import axios from 'axios';

// Register ChartJS components
ChartJS.register(
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend
);

const MSIScatterPlot = ({ stateCode }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/msi-analysis/${stateCode}`);
        
        // Transform the data for the scatter plot
        const scatterData = [
          {
            label: 'Price-to-Rent vs Investment Score',
            datasets: [
              {
                label: 'MSI Investment Scores',
                data: response.data.msi_data.map(item => ({
                  x: item.price_to_rent_ratio,
                  y: item.investment_score,
                  msi: item.msi_name,
                  marketHeat: item.market_heat,
                  daysToPending: item.days_to_pending,
                  priceCuts: item.price_cuts_percent
                })),
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1,
                pointRadius: 6,
                pointHoverRadius: 8,
              }
            ],
            xLabel: 'Price-to-Rent Ratio'
          },
          {
            label: 'Market Heat vs Investment Score',
            datasets: [
              {
                label: 'MSI Investment Scores',
                data: response.data.msi_data.map(item => ({
                  x: item.market_heat,
                  y: item.investment_score,
                  msi: item.msi_name,
                  marketHeat: item.market_heat,
                  daysToPending: item.days_to_pending,
                  priceCuts: item.price_cuts_percent
                })),
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1,
                pointRadius: 6,
                pointHoverRadius: 8,
              }
            ],
            xLabel: 'Market Heat'
          },
          {
            label: 'Days to Pending vs Investment Score',
            datasets: [
              {
                label: 'MSI Investment Scores',
                data: response.data.msi_data.map(item => ({
                  x: item.days_to_pending,
                  y: item.investment_score,
                  msi: item.msi_name,
                  marketHeat: item.market_heat,
                  daysToPending: item.days_to_pending,
                  priceCuts: item.price_cuts_percent
                })),
                backgroundColor: 'rgba(255, 159, 64, 0.6)',
                borderColor: 'rgba(255, 159, 64, 1)',
                borderWidth: 1,
                pointRadius: 6,
                pointHoverRadius: 8,
              }
            ],
            xLabel: 'Days to Pending'
          }
        ];
        
        setData(scatterData);
        setLoading(false);
      } catch (err) {
        setError(err.response?.data?.error || 'Failed to fetch MSI data');
        setLoading(false);
      }
    };

    if (stateCode) {
      fetchData();
    }
  }, [stateCode]);

  const getOptions = (xLabel) => ({
    scales: {
      x: {
        title: {
          display: true,
          text: xLabel,
          font: {
            size: 14,
            weight: 'bold'
          }
        },
        min: 0,
      },
      y: {
        title: {
          display: true,
          text: 'Investment Score',
          font: {
            size: 14,
            weight: 'bold'
          }
        },
        min: 0,
        max: 1,
      }
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: (context) => {
            const point = context.raw;
            return [
              `MSI: ${point.msi}`,
              `Investment Score: ${point.y.toFixed(2)}`,
              `Market Heat: ${point.marketHeat.toFixed(2)}`,
              `Days to Pending: ${point.daysToPending.toFixed(0)}`,
              `Price Cuts %: ${point.priceCuts.toFixed(2)}`
            ];
          }
        }
      }
    }
  });

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <Paper elevation={3} sx={{ p: 3, my: 2 }}>
      <Box display="flex" flexDirection="column" gap={4}>
        <Typography variant="h6" align="center" gutterBottom>
          MSI Investment Analysis for {stateCode}
        </Typography>
        
        {data && data.map((chartData, index) => (
          <Box key={index}>
            <Typography variant="subtitle1" align="center" gutterBottom>
              {chartData.label}
            </Typography>
            <Scatter 
              data={chartData} 
              options={getOptions(chartData.xLabel)}
              height={300}
            />
          </Box>
        ))}
      </Box>
    </Paper>
  );
};

export default MSIScatterPlot;
