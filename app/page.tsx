'use client'

import { useState, useRef, useEffect } from 'react'
import { 
  ArrowUpTrayIcon, 
  PaperAirplaneIcon, 
  DocumentTextIcon, 
  ChatBubbleLeftRightIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  SignalIcon,
  ClockIcon,
  ChartBarIcon,
  StarIcon
} from '@heroicons/react/24/outline'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

interface EvaluationMetrics {
  relevance: { score: number; description: string }
  faithfulness: { score: number; description: string }
  completeness: { score: number; description: string }
  clarity: { score: number; description: string }
  retrieval: { score: number; description: string }
}

interface EvaluationData {
  timestamp: string
  metrics: EvaluationMetrics
  overall_score: number
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  evaluation?: EvaluationData
}

interface EvaluationSummary {
  total_evaluations: number
  average_scores: {
    relevance: number
    faithfulness: number
    completeness: number
    clarity: number
    retrieval: number
    overall: number
  }
  recent_scores: {
    relevance: number
    faithfulness: number
    completeness: number
    clarity: number
    retrieval: number
    overall: number
  }
  recent_trend: string
  last_evaluation: string | null
}

interface Document {
  name: string
  chunks: number
}

interface SystemStatus {
  backend: 'connected' | 'disconnected' | 'checking'
  qdrant: 'connected' | 'disconnected' | 'checking'
  lastCheck: Date | null
}

interface UploadProgress {
  stage: 'idle' | 'uploading' | 'processing' | 'embedding' | 'storing' | 'complete' | 'error'
  progress: number
  message: string
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [documents, setDocuments] = useState<Document[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    backend: 'checking',
    qdrant: 'checking',
    lastCheck: null
  })
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({
    stage: 'idle',
    progress: 0,
    message: ''
  })
  const [showEvaluation, setShowEvaluation] = useState(false)
  const [evaluationSummary, setEvaluationSummary] = useState<EvaluationSummary | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    checkSystemStatus()
    fetchDocuments()
    fetchEvaluationSummary()
    // Check system status every 30 seconds
    const interval = setInterval(checkSystemStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const checkSystemStatus = async () => {
    setSystemStatus(prev => ({ ...prev, backend: 'checking', qdrant: 'checking' }))
    
    try {
      // Check backend health
      const healthResponse = await axios.get(`${API_BASE_URL}/health`, { timeout: 5000 })
      
      setSystemStatus({
        backend: 'connected',
        qdrant: healthResponse.data.qdrant_status === 'connected' ? 'connected' : 'disconnected',
        lastCheck: new Date()
      })
    } catch (error) {
      console.error('System status check failed:', error)
      setSystemStatus({
        backend: 'disconnected',
        qdrant: 'disconnected',
        lastCheck: new Date()
      })
    }
  }

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/documents`)
      setDocuments(response.data.documents.map((name: string) => ({ name, chunks: 0 })))
    } catch (error) {
      console.error('Error fetching documents:', error)
    }
  }

  const fetchEvaluationSummary = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/evaluation/summary`)
      setEvaluationSummary(response.data)
    } catch (error) {
      console.error('Error fetching evaluation summary:', error)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    setUploadProgress({
      stage: 'uploading',
      progress: 10,
      message: 'Uploading file...'
    })

    const formData = new FormData()
    formData.append('file', file)

    try {
      setUploadProgress({
        stage: 'processing',
        progress: 30,
        message: 'Extracting text from PDF...'
      })

      const response = await axios.post(`${API_BASE_URL}/upload-pdf`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const uploadPercent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            setUploadProgress(prev => ({
              ...prev,
              progress: Math.min(uploadPercent, 25)
            }))
          }
        }
      })

      setUploadProgress({
        stage: 'embedding',
        progress: 70,
        message: 'Generating embeddings...'
      })

      // Simulate embedding progress
      setTimeout(() => {
        setUploadProgress({
          stage: 'storing',
          progress: 90,
          message: 'Storing in vector database...'
        })
      }, 1000)

      setTimeout(() => {
        setUploadProgress({
          stage: 'complete',
          progress: 100,
          message: `Successfully processed ${response.data.chunks} chunks!`
        })
      }, 2000)
      
      fetchDocuments()
      
      // Reset progress after showing completion
      setTimeout(() => {
        setUploadProgress({
          stage: 'idle',
          progress: 0,
          message: ''
        })
      }, 3000)

    } catch (error: any) {
      setUploadProgress({
        stage: 'error',
        progress: 0,
        message: `Error: ${error.response?.data?.detail || error.message}`
      })
      
      // Reset progress after showing error
      setTimeout(() => {
        setUploadProgress({
          stage: 'idle',
          progress: 0,
          message: ''
        })
      }, 5000)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return

    const userMessage: Message = { role: 'user', content: inputMessage.trim() }
    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: userMessage.content,
        conversation_history: messages.slice(-5).map(msg => ({
          role: msg.role,
          content: msg.content
        })),
        evaluate: showEvaluation
      })

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.response,
        sources: response.data.sources,
        evaluation: response.data.evaluation
      }

      setMessages(prev => [...prev, assistantMessage])
      
      // Refresh evaluation summary if evaluation was performed
      if (showEvaluation && response.data.evaluation) {
        fetchEvaluationSummary()
      }
    } catch (error: any) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || 'Failed to get response from server'}`
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const getStatusIcon = (status: 'connected' | 'disconnected' | 'checking') => {
    switch (status) {
      case 'connected':
        return <CheckCircleIcon className="h-4 w-4 text-green-500" />
      case 'disconnected':
        return <XCircleIcon className="h-4 w-4 text-red-500" />
      case 'checking':
        return <ArrowPathIcon className="h-4 w-4 text-yellow-500 animate-spin" />
    }
  }

  const getProgressBarColor = (stage: UploadProgress['stage']) => {
    switch (stage) {
      case 'complete':
        return 'bg-green-500'
      case 'error':
        return 'bg-red-500'
      default:
        return 'bg-blue-500'
    }
  }

  const formatScore = (score: number): string => {
    return (score * 100).toFixed(0) + '%'
  }

  const getScoreColor = (score: number): string => {
    if (score >= 0.7) return 'text-green-600'
    if (score >= 0.4) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreBadgeColor = (score: number): string => {
    if (score >= 0.7) return 'bg-green-100 text-green-800'
    if (score >= 0.4) return 'bg-yellow-100 text-yellow-800'
    return 'bg-red-100 text-red-800'
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm border-b p-4">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <ChatBubbleLeftRightIcon className="h-6 w-6 text-blue-600" />
            <h1 className="text-xl font-semibold text-gray-900">RAG Chat</h1>
          </div>
          
          {/* System Status Indicators */}
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center space-x-1">
                <SignalIcon className="h-4 w-4 text-gray-400" />
                <span className="text-gray-600">Backend:</span>
                {getStatusIcon(systemStatus.backend)}
                <span className={`${
                  systemStatus.backend === 'connected' ? 'text-green-600' : 
                  systemStatus.backend === 'disconnected' ? 'text-red-600' : 
                  'text-yellow-600'
                }`}>
                  {systemStatus.backend}
                </span>
              </div>
              
              <div className="flex items-center space-x-1">
                <span className="text-gray-600">Qdrant:</span>
                {getStatusIcon(systemStatus.qdrant)}
                <span className={`${
                  systemStatus.qdrant === 'connected' ? 'text-green-600' : 
                  systemStatus.qdrant === 'disconnected' ? 'text-red-600' : 
                  'text-yellow-600'
                }`}>
                  {systemStatus.qdrant}
                </span>
              </div>
              
              {systemStatus.lastCheck && (
                <div className="flex items-center space-x-1 text-gray-500">
                  <ClockIcon className="h-3 w-3" />
                  <span className="text-xs">
                    {systemStatus.lastCheck.toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>
            
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowEvaluation(!showEvaluation)}
                className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  showEvaluation 
                    ? 'bg-green-100 text-green-700 hover:bg-green-200' 
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <ChartBarIcon className="h-4 w-4" />
                <span>Metrics</span>
                {showEvaluation && <span className="text-xs bg-green-200 px-1 rounded">ON</span>}
              </button>
              
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading || systemStatus.backend !== 'connected'}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isUploading ? (
                  <ArrowPathIcon className="h-4 w-4 animate-spin" />
                ) : (
                  <ArrowUpTrayIcon className="h-4 w-4" />
                )}
                <span>{isUploading ? 'Processing...' : 'Upload PDF'}</span>
              </button>
            </div>
          </div>
        </div>
        
        {/* Upload Progress Bar */}
        {uploadProgress.stage !== 'idle' && (
          <div className="max-w-6xl mx-auto mt-4">
            <div className="bg-gray-200 rounded-full h-2 mb-2">
              <div 
                className={`h-2 rounded-full transition-all duration-300 ${getProgressBarColor(uploadProgress.stage)}`}
                style={{ width: `${uploadProgress.progress}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">{uploadProgress.message}</span>
              <span className="text-gray-500">{uploadProgress.progress}%</span>
            </div>
          </div>
        )}
      </header>

      <div className="flex-1 flex max-w-6xl mx-auto w-full">
        {/* Sidebar */}
        <aside className="w-64 bg-white shadow-sm border-r p-4">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Documents</h2>
          <div className="space-y-2 mb-6">
            {documents.length === 0 ? (
              <p className="text-gray-600 text-sm">No documents uploaded yet</p>
            ) : (
              documents.map((doc, index) => (
                <div key={index} className="flex items-center space-x-2 p-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                  <DocumentTextIcon className="h-4 w-4 text-gray-700" />
                  <span className="text-sm text-gray-900 truncate font-medium" title={doc.name}>
                    {doc.name}
                  </span>
                </div>
              ))
            )}
          </div>

          {/* Evaluation Summary */}
          {showEvaluation && evaluationSummary && (
            <div className="border-t pt-4">
              <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
                <ChartBarIcon className="h-4 w-4 mr-2 text-blue-600" />
                Evaluation Summary
              </h3>
              
              <div className="space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Total Evaluations:</span>
                  <span className="font-medium text-gray-900">{evaluationSummary.total_evaluations}</span>
                </div>
                
                {evaluationSummary.total_evaluations > 0 && (
                  <>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Overall Score:</span>
                      <span className={`font-bold ${getScoreColor(evaluationSummary.average_scores.overall)}`}>
                        {formatScore(evaluationSummary.average_scores.overall)}
                      </span>
                    </div>
                    
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Trend:</span>
                      <span className={`font-medium ${
                        evaluationSummary.recent_trend === 'Improving' ? 'text-green-600' : 
                        evaluationSummary.recent_trend === 'Declining' ? 'text-red-600' : 
                        'text-gray-600'
                      }`}>
                        {evaluationSummary.recent_trend}
                      </span>
                    </div>
                    
                    <div className="mt-3 space-y-1">
                      <p className="text-gray-700 font-medium text-xs">Recent Metrics:</p>
                      {Object.entries(evaluationSummary.recent_scores).map(([metric, score]) => {
                        if (metric === 'overall') return null
                        return (
                          <div key={metric} className="flex justify-between items-center">
                            <span className="text-gray-600 capitalize">{metric}:</span>
                            <span className={`font-medium ${getScoreColor(score as number)}`}>
                              {formatScore(score as number)}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </aside>

        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-700 mt-8">
                <ChatBubbleLeftRightIcon className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <h3 className="text-lg font-semibold mb-2 text-gray-900">Welcome to RAG Chat</h3>
                <p className="text-gray-600">Upload a PDF document and start asking questions about its content.</p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-3xl p-4 rounded-lg ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white border shadow-sm text-gray-900'
                    }`}
                  >
                    <div className="whitespace-pre-wrap text-base leading-relaxed">{message.content}</div>
                    
                    {/* Evaluation Metrics */}
                    {message.evaluation && showEvaluation && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <div className="flex items-center justify-between mb-2">
                          <p className="text-xs text-gray-600 font-medium flex items-center">
                            <StarIcon className="h-3 w-3 mr-1" />
                            Evaluation Metrics
                          </p>
                          <span className={`text-xs font-bold px-2 py-1 rounded ${getScoreBadgeColor(message.evaluation.overall_score)}`}>
                            Overall: {formatScore(message.evaluation.overall_score)}
                          </span>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-1 text-xs">
                          {Object.entries(message.evaluation.metrics).map(([metric, data]) => (
                            <div key={metric} className="flex justify-between items-center">
                              <span className="text-gray-600 capitalize">{metric}:</span>
                              <span className={`font-medium ${getScoreColor(data.score)}`}>
                                {formatScore(data.score)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-200">
                        <p className="text-xs text-gray-600 mb-1 font-medium">Sources:</p>
                        <div className="flex flex-wrap gap-1">
                          {message.sources.map((source, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded font-medium"
                            >
                              {source}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white border shadow-sm p-4 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <ArrowPathIcon className="h-4 w-4 animate-spin text-blue-500" />
                    <span className="text-gray-700 font-medium">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t bg-white p-4">
            {systemStatus.backend !== 'connected' && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-300 rounded-lg">
                <div className="flex items-center space-x-2">
                  <ExclamationTriangleIcon className="h-5 w-5 text-yellow-700" />
                  <span className="text-yellow-900 text-sm font-semibold">
                    Backend service is {systemStatus.backend}. Please ensure the server is running.
                  </span>
                </div>
              </div>
            )}
            
            <div className="flex space-x-2">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={
                  systemStatus.backend === 'connected' 
                    ? "Ask a question about your documents..." 
                    : "Connect to backend to start chatting..."
                }
                className={`flex-1 resize-none border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:border-transparent text-gray-900 placeholder-gray-500 ${
                  systemStatus.backend === 'connected' 
                    ? 'border-gray-300 focus:ring-blue-500 bg-white' 
                    : 'border-red-300 bg-gray-50 focus:ring-red-500 text-gray-600'
                }`}
                rows={2}
                disabled={isLoading || systemStatus.backend !== 'connected'}
              />
              <button
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isLoading || systemStatus.backend !== 'connected'}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                <PaperAirplaneIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
