import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Select, message, Popconfirm, Card, Typography } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import UserForm from '../components/UserForm';
import { getUsers, createUser, updateUser, deleteUser } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const UserDashboard = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterGender, setFilterGender] = useState('All');
  
  // Modal state
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState(null);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      // Show only deleted = false 
      const params = { deleted: false };
      
      if (filterGender !== 'All') {
        params.gender = filterGender;
      }
      
      const response = await getUsers(params);
      
      // FeathersJS paginated response format: { total, limit, skip, data: [] }
      const usersData = response.data || [];
      setUsers(usersData);
    } catch (error) {
      console.error(error);
      message.error('Failed to fetch users. Please ensure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterGender]);

  const handleAdd = () => {
    setEditingUser(null);
    setIsModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingUser(record);
    setIsModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      await deleteUser(id);
      message.success('User deleted successfully');
      // Remove user from UI immediately without refreshing
      setUsers((prevUsers) => prevUsers.filter(user => user.id !== id));
    } catch (error) {
      console.error(error);
      message.error('Failed to delete user');
    }
  };

  const handleModalSubmit = async (values) => {
    try {
      if (editingUser) {
        // Edit User -> PATCH
        const updatedUser = await updateUser(editingUser.id, values);
        // Update UI instantly
        setUsers((prevUsers) => prevUsers.map(user => (user.id === editingUser.id ? updatedUser : user)));
        message.success('User updated successfully');
      } else {
        // Add User -> POST
        const newUser = await createUser(values);
        // Update table instantly
        setUsers((prevUsers) => [...prevUsers, newUser]);
        message.success('User added successfully');
      }
      setIsModalVisible(false);
    } catch (error) {
      console.error(error);
      message.error(editingUser ? 'Failed to update user' : 'Failed to add user');
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'Gender',
      dataIndex: 'gender',
      key: 'gender',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="middle">
          <Button 
            type="primary" 
            icon={<EditOutlined />} 
            onClick={() => handleEdit(record)}
            ghost
          >
            Edit
          </Button>
          <Popconfirm
            title="Are you sure you want to delete this user?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card 
      style={{ maxWidth: 1000, margin: '0 auto', borderRadius: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>User Management Dashboard</Title>
        <Space>
          <Select 
            value={filterGender} 
            onChange={(value) => setFilterGender(value)} 
            style={{ width: 120 }}
          >
            <Option value="All">All Genders</Option>
            <Option value="Male">Male</Option>
            <Option value="Female">Female</Option>
          </Select>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            Add User
          </Button>
        </Space>
      </div>

      <Table 
        columns={columns} 
        dataSource={users} 
        rowKey="id" 
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      <UserForm 
        visible={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onSubmit={handleModalSubmit}
        initialValues={editingUser}
      />
    </Card>
  );
};

export default UserDashboard;
