import type {
  Message,
  Conversation,
  QuestionsPayload,
  PlanTask,
  Resource,
  ContextUsage,
  SearchBudget,
  Project,
  TodoApprovalPayload,
  AgentEvent,
} from '../types';
import type { Mode } from '../components/InputArea';

export type ConvStatus = 'idle' | 'processing' | 'waiting_approval' | 'waiting_input';

export interface ChatContextType {
  messages: Message[];
  conversations: Conversation[];
  currentConvUuid: string | null;
  convStatuses: Record<string, ConvStatus>;
  questionsPayload: QuestionsPayload | null;
  tasks: PlanTask[];
  resources: Resource[];
  rightPanelOpen: boolean;
  contextUsage: ContextUsage | null;
  searchBudget: SearchBudget | null;
  viewingReport: Resource | null;
  inputMode: Mode;
  inputText: string;
  approvalEvent: AgentEvent | null;
  todoApprovalPayload: TodoApprovalPayload | null;
  mobileSidebarOpen: boolean;
  mobileRightOpen: boolean;
  conversationLoading: boolean;
  connected: boolean;
  effectiveProcessing: boolean;
  effectiveTurnActive: boolean;
  loadConversations: (project?: Project | null) => Promise<Conversation[]>;
  switchConv: (uuid: string) => Promise<void>;
  handleSwitchConversation: (uuid: string) => void;
  handleNewConversation: () => Promise<void>;
  handleDeleteConversation: (uuid: string) => Promise<void>;
  sendMessage: (text: string, mode: string, mentions?: Array<{ type: 'server' | 'file'; value: string }>) => Promise<void>;
  handleStop: () => void;
  setInputMode: (mode: Mode) => void;
  setInputText: (text: string) => void;
  setRightPanelOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setMobileSidebarOpen: (open: boolean) => void;
  setMobileRightOpen: (open: boolean) => void;
  setApprovalEvent: (event: AgentEvent | null) => void;
  setQuestionsPayload: (p: QuestionsPayload | null) => void;
  setTodoApprovalPayload: (p: TodoApprovalPayload | null) => void;
  setViewingReport: (r: Resource | null) => void;
  handleSearchBudgetChange: (newMax: number) => void;
  reloadConversationMessages: (uuid: string) => void;
  setCurrentConvStatus: (status: ConvStatus) => void;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
}
