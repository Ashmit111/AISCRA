import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Suppliers from './pages/Suppliers'
import Alerts from './pages/Alerts'
import Agent from './pages/Agent'
import Reports from './pages/Reports'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/suppliers" element={<Suppliers />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/agent" element={<Agent />} />
        <Route path="/reports" element={<Reports />} />
      </Routes>
    </Layout>
  )
}

export default App
