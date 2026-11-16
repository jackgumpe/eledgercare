const apiPort = process.env['ELEDGERCARE_API_PORT'] ?? '5390';

export default {
  '/api': {
    target: `http://127.0.0.1:${apiPort}`,
    secure: false,
    changeOrigin: true,
  },
};
