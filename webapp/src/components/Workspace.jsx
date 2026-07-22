import React, { useState, useRef, useEffect } from 'react';
import { 
  PenTool, FileText, Upload, Send, Trash2, Save, FilePlus, 
  ChevronLeft, ChevronRight, LogOut, Printer, Settings, Sparkles
} from 'lucide-react';

export default function Workspace({ user, onLogout, savedDocs, onSaveDoc, onDeleteDoc, onNavigate }) {
  // Document state
  const [docId, setDocId] = useState(null);
  const [title, setTitle] = useState("Untitled Handwriting");
  const [text, setText] = useState(
    "Dear Friend,\n\nWelcome to ScribbleAI. This is your personal handwriting playground!\n\nYou can edit this text directly, drag and drop a plain text file into the extractor on the left, or use the interactive AI assistant chat below to draft letters for you.\n\nAdjust the sliders in the configuration panel to change the cursive style, ink tone, margin size, scale, and letter tilt. Everything updates dynamically in real-time.\n\nWarm regards,\nThe ScribbleAI Team"
  );
  
  // Customization settings
  const [font, setFont] = useState("Caveat");
  const [inkColor, setInkColor] = useState("ink-blue");
  const [paperType, setPaperType] = useState("paper-lined");
  const [fontSize, setFontSize] = useState(24);
  const [lineHeight, setLineHeight] = useState(28);
  const [marginLeft, setMarginLeft] = useState(115); // Left margin, adjusted for binder rings
  const [skewValue, setSkewValue] = useState(-0.5); // Letter tilt
  const [letterSpacing, setLetterSpacing] = useState(0.5);

  // Chat/AI State
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState([
    { 
      id: 1, 
      sender: 'ai', 
      text: "Hello! I am your AI Handwriting Assistant. Ask me to help write templates or style pages. For example, try saying:\n• 'write a thank you letter'\n• 'change ink to forest green'\n• 'change paper to graph grid'" 
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);

  // File Upload State
  const [isDragging, setIsDragging] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // References
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Load selected document
  const handleLoadDoc = (doc) => {
    setDocId(doc.id);
    setTitle(doc.title);
    setText(doc.text_content);
    setFont(doc.font_style || "Caveat");
    setInkColor(doc.ink_color || "ink-blue");
    setPaperType(doc.paper_type || "paper-lined");
    setFontSize(doc.font_size || 24);
    setLineHeight(doc.line_height || 28);
    setMarginLeft(doc.margin_left || 115);
    setSkewValue(doc.skew_value || -0.5);
    setLetterSpacing(doc.letter_spacing || 0.5);
  };

  // Create new blank document
  const handleNewDoc = () => {
    setDocId(null);
    setTitle("New Cursive Draft");
    setText("");
    setFont("Caveat");
    setInkColor("ink-blue");
    setPaperType("paper-lined");
    setFontSize(24);
    setLineHeight(28);
    setMarginLeft(115);
    setSkewValue(-0.5);
    setLetterSpacing(0.5);
  };

  // Save current doc
  const handleSave = () => {
    const docData = {
      id: docId || Math.random().toString(36).substring(7),
      title,
      text_content: text,
      font_style: font,
      ink_color: inkColor,
      paper_type: paperType,
      font_size: fontSize,
      line_height: lineHeight,
      margin_left: marginLeft,
      skew_value: skewValue,
      letter_spacing: letterSpacing,
      updated_at: new Date().toISOString()
    };
    onSaveDoc(docData);
    if (!docId) setDocId(docData.id);
  };

  // Text File Extraction
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    processFile(file);
  };

  const processFile = (file) => {
    if (!file) return;
    if (file.type !== "text/plain" && !file.name.endsWith('.txt')) {
      alert("Please upload a standard plain text (.txt) file.");
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      setText(event.target.result);
      const lines = event.target.result.split('\n');
      const firstLine = lines[0].trim().substring(0, 24);
      setTitle(firstLine || file.name.replace('.txt', ''));
    };
    reader.readAsText(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    processFile(file);
  };

  // Export PDF (Print layout)
  const handlePrint = () => {
    window.print();
  };

  // Handle Mock Chat Commands
  const handleSendChat = (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput;
    setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text: userMsg }]);
    setChatInput("");
    setIsTyping(true);

    setTimeout(() => {
      let replyText = "I've processed your message.";
      const query = userMsg.toLowerCase();

      if (query.includes("thank you") || query.includes("thanks")) {
        const textDraft = "Dear Friends,\n\nI wanted to express my sincere gratitude for your wonderful support. Your help made a significant difference, and I am truly thankful.\n\nBest regards,\nYour Name";
        setText(textDraft);
        setTitle("Thank You Letter");
        replyText = "✨ I've drafted a premium thank you letter on your canvas. Feel free to adjust the handwriting style!";
      } 
      else if (query.includes("apology") || query.includes("sorry")) {
        const textDraft = "Dear Team,\n\nPlease accept my sincere apologies for missing the meeting earlier today. An unexpected emergency arose, preventing my attendance.\n\nI will review the minutes and follow up promptly.\n\nSincerely,\nYour Name";
        setText(textDraft);
        setTitle("Apology Letter");
        replyText = "✍️ Sure, I have written a casual apology note on your paper. Let me know if you need any adjustments.";
      }
      else if (query.includes("love") || query.includes("valentine") || query.includes("poem")) {
        const textDraft = "My Dearest,\n\nHow do I love thee? Let me count the ways.\nI love thee to the depth and breadth and height\nMy soul can reach, when feeling out of sight\nFor the ends of being and ideal grace.\n\nForever yours,\nYour Valentine";
        setText(textDraft);
        setTitle("Love Poem");
        replyText = "💖 Here is a classic romantic love poem written out for you.";
      }
      else if (query.includes("blue ink") || query.includes("blue color")) {
        setInkColor("ink-blue");
        replyText = "🎨 Ink shade updated to Royal Blue.";
      }
      else if (query.includes("black ink") || query.includes("black color")) {
        setInkColor("ink-black");
        replyText = "🎨 Ink shade updated to Classic Black.";
      }
      else if (query.includes("red ink") || query.includes("red color")) {
        setInkColor("ink-red");
        replyText = "🎨 Ink shade updated to Deep Red.";
      }
      else if (query.includes("green ink") || query.includes("green color")) {
        setInkColor("ink-green");
        replyText = "🎨 Ink shade updated to Forest Green.";
      }
      else if (query.includes("lined") || query.includes("notebook")) {
        setPaperType("paper-lined");
        replyText = "📄 Paper backing changed to Lined Notebook.";
      }
      else if (query.includes("graph") || query.includes("grid")) {
        setPaperType("paper-grid");
        replyText = "📄 Paper backing changed to Graph Grid.";
      }
      else if (query.includes("plain") || query.includes("parchment")) {
        setPaperType("paper-plain");
        replyText = "📄 Paper backing changed to Clean Parchment.";
      }
      else if (query.includes("font") || query.includes("style")) {
        if (query.includes("print")) {
          setFont("Patrick Hand");
          replyText = "✒️ Writing style updated to Neat Print.";
        } else if (query.includes("sketch") || query.includes("informal")) {
          setFont("Reenie Beanie");
          replyText = "✒️ Writing style updated to Informal Sketch.";
        } else if (query.includes("calligraphy") || query.includes("elegant")) {
          setFont("Sacramento");
          replyText = "✒️ Writing style updated to Elegant Calligraphy.";
        } else {
          setFont("Homemade Apple");
          replyText = "✒️ Writing style updated to Real Cursive.";
        }
      } 
      else {
        replyText = `✍️ Understood! You can directly edit the paper canvas, upload custom files, or use the styling parameters on the right to tailor the layout.`;
      }

      setMessages(prev => [...prev, { id: Date.now(), sender: 'ai', text: replyText }]);
      setIsTyping(false);
    }, 1000);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-base)] relative" id="workspace-page">
      {/* Dynamic pastel aura circles behind workspace */}
      <div className="absolute top-[20%] left-[25%] w-[350px] h-[350px] rounded-full bg-[var(--periwinkle-light)] opacity-30 filter blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-[10%] right-[30%] w-[450px] h-[450px] rounded-full bg-[var(--butter-light)] opacity-35 filter blur-3xl pointer-events-none"></div>

      {/* Sidebar Drawer */}
      <div 
        className={`glass-panel h-full flex flex-col transition-all duration-300 z-10 border-r border-slate-200/50 workspace-sidebar-active ${
          sidebarOpen ? 'w-64' : 'w-0 overflow-hidden border-none'
        }`}
        style={{ borderRadius: '0px', backgroundColor: 'rgba(255, 255, 255, 0.85)' }}
        id="workspace-sidebar"
      >
        {/* Sidebar Header */}
        <div className="p-5 border-b border-slate-200/40 flex justify-between items-center shrink-0">
          <div className="flex items-center gap-2 font-extrabold text-xl text-[var(--text-main)] italic">
            <span className="p-2 bg-gradient-to-tr from-[var(--periwinkle-light)] to-white rounded-xl inline-flex items-center justify-center shadow-sm">
              <PenTool size={18} className="text-[var(--periwinkle-glow)]" />
            </span>
            Scribble<span className="text-[var(--periwinkle-glow)]">AI</span>
          </div>
          <button 
            onClick={handleNewDoc}
            className="p-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-white transition-all shadow-sm"
            title="Create New Document"
            id="sidebar-new-doc-btn"
          >
            <FilePlus size={18} />
          </button>
        </div>

        {/* Saved Documents List */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-2">
          <span className="text-[10px] font-bold text-[var(--text-light)] px-2 py-1 uppercase tracking-wider text-left">My Cursive Archives</span>
          {savedDocs.length === 0 ? (
            <div className="text-center text-xs text-[var(--text-light)] py-12 px-4 bg-white/30 rounded-2xl border border-dashed border-slate-200/40">
              No saved documents yet. Write something and hit Save!
            </div>
          ) : (
            savedDocs.map(doc => (
              <div 
                key={doc.id}
                onClick={() => handleLoadDoc(doc)}
                className={`group flex justify-between items-center p-3 rounded-2xl cursor-pointer transition-all duration-200 border ${
                  docId === doc.id 
                    ? 'bg-white border-slate-200/60 text-[var(--periwinkle-glow)] font-bold shadow-sm' 
                    : 'border-transparent text-[var(--text-muted)] hover:bg-white/50 hover:text-[var(--text-main)]'
                }`}
              >
                <div className="flex items-center gap-2.5 truncate text-xs">
                  <FileText size={14} className={docId === doc.id ? "text-[var(--periwinkle-glow)]" : "text-[var(--text-light)]"} />
                  <span className="truncate">{doc.title}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteDoc(doc.id);
                    if (docId === doc.id) handleNewDoc();
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-50 hover:text-red-500 transition-all"
                  title="Delete Document"
                  id={`delete-doc-${doc.id}`}
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))
          )}
        </div>

        {/* User Info & Footer */}
        <div className="p-4 border-t border-slate-200/40 flex flex-col gap-3 shrink-0 bg-white/50">
          <div className="flex items-center justify-between p-2.5 rounded-xl bg-white/60 border border-slate-200/30 text-xs">
            <span className="truncate max-w-[120px] font-bold text-[var(--text-main)]">
              {user ? user.email : 'Guest Explorer'}
            </span>
            <button 
              onClick={onLogout}
              className="flex items-center gap-1 text-[#E57373] hover:text-red-500 font-semibold"
              id="sidebar-logout-btn"
            >
              <LogOut size={12} />
              Exit
            </button>
          </div>
          <button
            onClick={() => onNavigate('landing')}
            className="w-full text-center py-2.5 rounded-xl bg-[var(--periwinkle-light)] text-[var(--periwinkle-glow-hover)] font-bold text-xs hover:bg-[var(--periwinkle)] border border-[var(--periwinkle-dark)]/40 transition-colors"
          >
            Back to Landing Page
          </button>
        </div>
      </div>

      {/* Toggle Sidebar Button */}
      <button 
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="absolute top-1/2 -translate-y-1/2 left-0 z-20 w-6 h-14 bg-white border border-slate-200/60 shadow-lg rounded-r-xl flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-main)] transition-all"
        style={{ left: sidebarOpen ? '256px' : '0px', transition: 'left 0.4s var(--ease-elastic)' }}
        id="toggle-sidebar-btn"
      >
        {sidebarOpen ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
      </button>

      {/* Main Workspace Layout */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        
        {/* Top Control Bar */}
        <header className="h-20 px-8 bg-white/80 backdrop-blur-md border-b border-slate-200/40 flex items-center justify-between shrink-0 z-5">
          <div className="flex items-center gap-4">
            <input 
              type="text" 
              value={title} 
              onChange={(e) => setTitle(e.target.value)}
              className="bg-transparent border-none text-[var(--text-main)] font-extrabold text-xl focus:outline-none focus:border-b-2 border-[var(--periwinkle-glow)] py-1 transition-all"
              placeholder="Untitled Handwriting..."
              id="workspace-doc-title-input"
            />
          </div>
          <div className="flex items-center gap-3">
            <button 
              onClick={handleSave}
              className="btn-secondary"
              id="workspace-save-btn"
            >
              <Save size={14} />
              Save to Cloud
            </button>
            <button 
              onClick={handlePrint}
              className="btn-primary"
              id="workspace-print-btn"
            >
              <Printer size={14} />
              Print / PDF Export
            </button>
          </div>
        </header>

        {/* Content Panels */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          
          {/* Left panel: Chat assistant & Text extraction */}
          <div className="w-full md:w-[360px] border-r border-slate-200/30 flex flex-col h-full shrink-0 bg-white/50 backdrop-blur-md z-2">
            
            {/* Tabs / Modules */}
            <div className="flex-1 flex flex-col overflow-hidden">
              
              {/* File Extractor Header */}
              <div className="p-5 border-b border-slate-200/30 bg-white/20">
                <span className="text-[10px] font-bold text-[var(--text-light)] block mb-2.5 uppercase tracking-wider text-left">Document Source Extractor</span>
                <div 
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-2xl p-5 text-center cursor-pointer transition-all duration-300 ${
                    isDragging 
                      ? 'border-[var(--periwinkle-glow)] bg-[var(--periwinkle-light)] shadow-inner' 
                      : 'border-slate-200/80 hover:border-[var(--periwinkle-glow)]/50 bg-white/40'
                  }`}
                  id="drag-drop-zone"
                >
                  <Upload size={24} className="mx-auto mb-2 text-[var(--periwinkle-glow)]" />
                  <p className="text-xs font-bold text-[var(--text-main)]">Drag & Drop text file here</p>
                  <p className="text-[10px] text-[var(--text-light)] mt-1">Supports standard plain .txt files</p>
                  <input 
                    type="file" 
                    ref={fileInputRef} 
                    onChange={handleFileUpload} 
                    accept=".txt"
                    className="hidden"
                    id="file-upload-input"
                  />
                </div>
              </div>

              {/* Chat View */}
              <div className="flex-1 flex flex-col overflow-hidden min-h-[220px]">
                <div className="px-5 py-3.5 border-b border-slate-200/30 bg-white/20 flex justify-between items-center shrink-0">
                  <span className="text-[10px] font-bold text-[var(--text-light)] uppercase tracking-wider">AI Assistant Chat</span>
                  <span className="p-1 bg-[#E7F6EC] text-[#2E7D32] rounded-full text-[9px] font-bold px-2.5 flex items-center gap-1">
                    <Sparkles size={10} /> Active
                  </span>
                </div>
                
                {/* Chat Log */}
                <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4 bg-slate-50/20">
                  {messages.map(msg => (
                    <div 
                      key={msg.id}
                      className={`flex flex-col max-w-[88%] ${
                        msg.sender === 'user' ? 'self-end items-end' : 'self-start items-start'
                      }`}
                    >
                      <div className={`p-3.5 rounded-2xl text-xs text-left shadow-sm border whitespace-pre-wrap leading-relaxed ${
                        msg.sender === 'user'
                          ? 'bg-[var(--periwinkle-light)] border-[var(--periwinkle)]/60 text-[var(--text-main)] rounded-tr-none'
                          : 'bg-white border-slate-200/50 text-[var(--text-main)] rounded-tl-none'
                      }`}>
                        {msg.text}
                      </div>
                    </div>
                  ))}
                  {isTyping && (
                    <div className="self-start flex gap-1.5 items-center p-3 rounded-2xl bg-white border border-slate-200/40 px-4 shadow-sm">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--periwinkle-glow)] animate-bounce" style={{ animationDelay: '0ms' }}></span>
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--periwinkle-glow)] animate-bounce" style={{ animationDelay: '150ms' }}></span>
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--periwinkle-glow)] animate-bounce" style={{ animationDelay: '300ms' }}></span>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Chat Input */}
                <form onSubmit={handleSendChat} className="p-4 border-t border-slate-200/30 flex gap-2 shrink-0 bg-white">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Ask AI to compose or style pages..."
                    className="flex-1 px-4 py-3 rounded-xl bg-slate-50 border border-slate-100 text-xs text-[var(--text-main)] placeholder-[var(--text-light)] focus:outline-none focus:border-[var(--periwinkle-glow)] focus:bg-white transition-all"
                    id="chat-message-input"
                  />
                  <button 
                    type="submit" 
                    className="p-3 rounded-xl bg-[var(--periwinkle-light)] text-[var(--text-main)] hover:bg-[var(--periwinkle)] transition-all flex items-center justify-center"
                    id="chat-send-btn"
                  >
                    <Send size={14} className="text-[var(--periwinkle-glow)]" />
                  </button>
                </form>
              </div>

            </div>
          </div>

          {/* Right Panel: Content preview on paper & sliders */}
          <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
            
            {/* Paper Preview Sheet Workspace */}
            <div className="flex-1 p-6 md:p-10 overflow-y-auto flex justify-center items-start bg-slate-100/40">
              
              {/* Paper Element Container */}
              <div 
                className={`printable-paper w-full max-w-[650px] min-h-[840px] p-12 transition-all duration-300 relative ${paperType}`}
                style={{
                  paddingLeft: `${marginLeft}px`,
                  boxShadow: '0 10px 40px rgba(0,0,0,0.04), 0 25px 70px rgba(0,0,0,0.06)'
                }}
                id="handwriting-paper-canvas"
              >
                {/* Spiral Binder Rings on Left Side (adds hyper-realism) */}
                {(paperType === 'paper-lined' || paperType === 'paper-grid') && (
                  <div className="absolute left-[15px] top-6 bottom-6 w-[25px] flex flex-col justify-between pointer-events-none select-none z-10" style={{ opacity: 0.85 }}>
                    {Array.from({ length: 18 }).map((_, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 h-6">
                        {/* Metal ring hole on paper */}
                        <div className="w-2.5 h-2.5 rounded-full bg-slate-300 shadow-inner border border-slate-400/20"></div>
                        {/* Spiral metal ring loop */}
                        <div className="w-8 h-2 rounded-full bg-gradient-to-b from-slate-400 via-slate-100 to-slate-400/80 shadow-md border border-slate-400/20 transform rotate-[18deg] -translate-y-0.5"></div>
                      </div>
                    ))}
                  </div>
                )}

                {/* SVG Filter for Ink Bleed */}
                <svg className="hidden">
                  <defs>
                    <filter id="inkbleed">
                      <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" result="noise" />
                      <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.2" xChannelSelector="R" yChannelSelector="G" />
                    </filter>
                  </defs>
                </svg>

                {/* Raw Editable/Display overlay */}
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  className={`w-full h-full bg-transparent border-none outline-none resize-none font-medium ${inkColor}`}
                  style={{
                    fontFamily: font,
                    fontSize: `${fontSize}px`,
                    lineHeight: `${lineHeight}px`,
                    letterSpacing: `${letterSpacing}px`,
                    transform: `rotate(${skewValue}deg)`,
                    transformOrigin: 'top left',
                    filter: 'url(#inkbleed)',
                    minHeight: '750px',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                  placeholder="Start writing your handwritten letter here..."
                  id="paper-canvas-textarea"
                />
              </div>

            </div>

            {/* Slider Config Sidebar */}
            <div className="w-full lg:w-[290px] bg-white border-l border-slate-200/40 p-6 overflow-y-auto shrink-0 flex flex-col gap-6 text-left shadow-sm">
              <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
                <Settings size={18} className="text-[var(--periwinkle-glow)]" />
                <span className="text-sm font-extrabold text-[var(--text-main)]">Canvas Customization</span>
              </div>

              {/* Style controls */}
              <div className="flex flex-col gap-5">
                {/* Font selector */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-[#64748B]">Font Style</label>
                  <select 
                    value={font} 
                    onChange={(e) => setFont(e.target.value)}
                    className="p-3 rounded-xl bg-slate-50 border border-slate-200/50 text-xs text-[var(--text-main)] focus:outline-none focus:border-[var(--periwinkle-glow)]"
                    id="config-font-select"
                  >
                    <option value="Caveat">Playful Cursive (Caveat)</option>
                    <option value="Homemade Apple">Real Handwriting (Homemade Apple)</option>
                    <option value="Sacramento">Elegant Calligraphy (Sacramento)</option>
                    <option value="Patrick Hand">Neat Print (Patrick Hand)</option>
                    <option value="Reenie Beanie">Sketchy/Hurried (Reenie Beanie)</option>
                    <option value="Delius">Modern Sans (Delius)</option>
                  </select>
                </div>

                {/* Ink Color Grid */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-[#64748B]">Ink Color</label>
                  <div className="flex gap-2.5 py-0.5">
                    {[
                      { name: 'Royal Blue', class: 'ink-blue', color: '#1e3a80' },
                      { name: 'Classic Black', class: 'ink-black', color: '#212529' },
                      { name: 'Crimson Red', class: 'ink-red', color: '#922b2b' },
                      { name: 'Forest Green', class: 'ink-green', color: '#1b4d3e' }
                    ].map(item => (
                      <button
                        key={item.class}
                        onClick={() => setInkColor(item.class)}
                        className={`w-8 h-8 rounded-full border-2 transition-all ${inkColor === item.class ? 'border-[var(--periwinkle-glow)] scale-110 shadow-md' : 'border-transparent hover:scale-105'}`}
                        style={{ backgroundColor: item.color }}
                        title={item.name}
                        id={`config-ink-color-${item.class}`}
                      />
                    ))}
                  </div>
                </div>

                {/* Paper Grid */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-[#64748B]">Paper Canvas Background</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { name: 'Lined', value: 'paper-lined' },
                      { name: 'Grid', value: 'paper-grid' },
                      { name: 'Plain', value: 'paper-plain' }
                    ].map(item => (
                      <button
                        key={item.value}
                        onClick={() => setPaperType(item.value)}
                        className={`py-2.5 rounded-xl text-xs font-bold border transition-all ${
                          paperType === item.value 
                            ? 'bg-[var(--periwinkle-light)] border-[var(--periwinkle-glow)] text-[var(--periwinkle-glow)] shadow-sm' 
                            : 'bg-slate-50 border-slate-200/40 text-[#64748B] hover:bg-slate-100'
                        }`}
                        id={`config-paper-${item.value}`}
                      >
                        {item.name}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="border-t border-slate-100 my-1"></div>

                {/* Sliders */}
                
                {/* Font Size */}
                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="font-bold text-[#64748B]">Font Size</span>
                    <span className="font-bold text-[var(--text-main)]">{fontSize}px</span>
                  </div>
                  <input 
                    type="range" 
                    min="16" 
                    max="40" 
                    value={fontSize}
                    onChange={(e) => setFontSize(parseInt(e.target.value))}
                    id="config-font-size-slider"
                  />
                </div>

                {/* Line Height */}
                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="font-bold text-[#64748B]">Line Height</span>
                    <span className="font-bold text-[var(--text-main)]">{lineHeight}px</span>
                  </div>
                  <input 
                    type="range" 
                    min="20" 
                    max="60" 
                    value={lineHeight}
                    onChange={(e) => setLineHeight(parseInt(e.target.value))}
                    id="config-line-height-slider"
                  />
                </div>

                {/* Left Margin */}
                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="font-bold text-[#64748B]">Left Margin Padding</span>
                    <span className="font-bold text-[var(--text-main)]">{marginLeft}px</span>
                  </div>
                  <input 
                    type="range" 
                    min="40" 
                    max="150" 
                    value={marginLeft}
                    onChange={(e) => setMarginLeft(parseInt(e.target.value))}
                    id="config-margin-left-slider"
                  />
                </div>

                {/* Tilt Skew */}
                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="font-bold text-[#64748B]">Handwriting Tilt (Skew)</span>
                    <span className="font-bold text-[var(--text-main)]">{skewValue}°</span>
                  </div>
                  <input 
                    type="range" 
                    min="-3" 
                    max="3" 
                    step="0.1"
                    value={skewValue}
                    onChange={(e) => setSkewValue(parseFloat(e.target.value))}
                    id="config-skew-slider"
                  />
                </div>

                {/* Letter Spacing */}
                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="font-bold text-[#64748B]">Letter Spacing</span>
                    <span className="font-bold text-[var(--text-main)]">{letterSpacing}px</span>
                  </div>
                  <input 
                    type="range" 
                    min="-1" 
                    max="4" 
                    step="0.1"
                    value={letterSpacing}
                    onChange={(e) => setLetterSpacing(parseFloat(e.target.value))}
                    id="config-letter-spacing-slider"
                  />
                </div>

              </div>
            </div>

          </div>

        </div>

      </div>

    </div>
  );
}
