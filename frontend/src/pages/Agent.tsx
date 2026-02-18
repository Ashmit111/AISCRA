import { useState, FormEvent } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Send, Sparkles } from 'lucide-react'

export default function Agent() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([])

  const { data: starters } = useQuery({
    queryKey: ['conversation-starters'],
    queryFn: api.getConversationStarters,
  })

  const queryMutation = useMutation({
    mutationFn: (query: string) => api.queryAgent(query, messages),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: input },
        { role: 'assistant', content: data.response }
      ])
      setInput('')
    }
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    queryMutation.mutate(input)
  }

  const handleStarterClick = (starter: string) => {
    setInput(starter)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">AI Agent</h1>
        <p className="text-muted-foreground">
          Ask questions about your supply chain risks in natural language
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Chat Interface */}
        <Card className="lg:col-span-2 flex flex-col h-[600px]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Supply Chain AI Assistant
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-4 mb-4">
              {messages.length === 0 ? (
                <div className="text-center text-muted-foreground py-12">
                  <Sparkles className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                  <p>Start a conversation by asking a question or selecting a starter below</p>
                </div>
              ) : (
                messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-2 ${
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted'
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                ))
              )}
              {queryMutation.isPending && (
                <div className="flex justify-start">
                  <div className="bg-muted rounded-lg px-4 py-2">
                    <p className="text-sm text-muted-foreground">Thinking...</p>
                  </div>
                </div>
              )}
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about supply chain risks..."
                className="flex-1 px-4 py-2 border rounded-md focus:outline focus:ring-2 focus:ring-primary"
                disabled={queryMutation.isPending}
              />
              <Button type="submit" disabled={queryMutation.isPending || !input.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Conversation Starters */}
        <Card>
          <CardHeader>
            <CardTitle>Suggested Questions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {starters?.map((starter, idx) => (
                <Button
                  key={idx}
                  variant="outline"
                  className="w-full justify-start text-left h-auto py-3 px-4"
                  onClick={() => handleStarterClick(starter)}
                >
                  <span className="text-sm">{starter}</span>
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
