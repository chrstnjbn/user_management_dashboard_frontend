import React from 'react';
import { ConfigProvider } from 'antd';
import UserDashboard from './pages/UserDashboard';
import './index.css';

function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1890ff',
        },
      }}
    >
      <div className="App" style={{ background: '#f0f2f5', minHeight: '100vh', padding: '24px' }}>
        <UserDashboard />
      </div>
    </ConfigProvider>
  );
}

export default App;
