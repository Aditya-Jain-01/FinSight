from app.agent.tools.company_info import get_company_info
from app.agent.tools.financials import get_financials
from app.agent.tools.rag_search import rag_search
from app.agent.tools.stock_news import get_stock_news
from app.agent.tools.stock_price import get_stock_price

TOOLS = [get_stock_price, get_financials, get_company_info, get_stock_news, rag_search]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}