"""
基于MongoDB的股票筛选服务
利用本地数据库中的股票基础信息进行高效筛选
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from app.core.database import get_mongo_db
# from app.models.screening import ScreeningCondition  # 避免循环导入

logger = logging.getLogger(__name__)


class DatabaseScreeningService:
    """基于数据库的股票筛选服务"""
    
    def __init__(self):
        self.collection_name = "stock_basic_info"
        
        # 支持的基础信息字段映射
        self.basic_fields = {
            # 基本信息
            "code": "code",
            "name": "name", 
            "industry": "industry",
            "area": "area",
            "market": "market",
            "list_date": "list_date",
            
            # 市值信息 (亿元)
            "total_mv": "total_mv",      # 总市值
            "circ_mv": "circ_mv",        # 流通市值
            "market_cap": "total_mv",    # 市值别名

            # 财务指标
            "pe": "pe",                  # 市盈率
            "pb": "pb",                  # 市净率
            "pe_ttm": "pe_ttm",         # 滚动市盈率
            "pb_mrq": "pb_mrq",         # 最新市净率
            "roe": "roe",                # 净资产收益率（最近一期）

            # 交易指标
            "turnover_rate": "turnover_rate",  # 换手率%
            "volume_ratio": "volume_ratio",    # 量比
        }
        
        # 支持的操作符
        self.operators = {
            ">": "$gt",
            "<": "$lt", 
            ">=": "$gte",
            "<=": "$lte",
            "==": "$eq",
            "!=": "$ne",
            "between": "$between",  # 自定义处理
            "in": "$in",
            "not_in": "$nin",
            "contains": "$regex",   # 字符串包含
        }
    
    async def can_handle_conditions(self, conditions: List[Dict[str, Any]]) -> bool:
        """
        检查是否可以完全通过数据库筛选处理这些条件
        
        Args:
            conditions: 筛选条件列表
            
        Returns:
            bool: 是否可以处理
        """
        for condition in conditions:
            field = condition.get("field") if isinstance(condition, dict) else condition.field
            operator = condition.get("operator") if isinstance(condition, dict) else condition.operator
            
            # 检查字段是否支持
            if field not in self.basic_fields:
                logger.debug(f"字段 {field} 不支持数据库筛选")
                return False
            
            # 检查操作符是否支持
            if operator not in self.operators:
                logger.debug(f"操作符 {operator} 不支持数据库筛选")
                return False
        
        return True
    
    async def screen_stocks(
        self,
        conditions: List[Dict[str, Any]],
        limit: int = 50,
        offset: int = 0,
        order_by: Optional[List[Dict[str, str]]] = None,
        source: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        基于数据库进行股票筛选

        Args:
            conditions: 筛选条件列表
            limit: 返回数量限制
            offset: 偏移量
            order_by: 排序条件 [{"field": "total_mv", "direction": "desc"}]
            source: 数据源（可选），默认使用优先级最高的数据源

        Returns:
            Tuple[List[Dict], int]: (筛选结果, 总数量)
        """
        try:
            db = get_mongo_db()
            collection = db[self.collection_name]

            # 🔥 获取数据源优先级配置
            if not source:
                from app.core.unified_config import UnifiedConfigManager
                config = UnifiedConfigManager()
                data_source_configs = await config.get_data_source_configs_async()

                logger.info(f"🔍 [database_screening] 获取到 {len(data_source_configs)} 个数据源配置")
                for ds in data_source_configs:
                    logger.info(f"   - {ds.name}: type={ds.type}, priority={ds.priority}, enabled={ds.enabled}")

                # 提取启用的数据源，按优先级排序
                enabled_sources = [
                    ds.type.lower() for ds in data_source_configs
                    if ds.enabled and ds.type.lower() in ['tushare', 'akshare', 'baostock']
                ]

                logger.info(f"🔍 [database_screening] 启用的数据源（按优先级）: {enabled_sources}")

                if not enabled_sources:
                    enabled_sources = ['tushare', 'akshare', 'baostock']
                    logger.warning(f"⚠️ [database_screening] 没有启用的数据源，使用默认: {enabled_sources}")

                source = enabled_sources[0] if enabled_sources else 'tushare'
                logger.info(f"✅ [database_screening] 最终使用的数据源: {source}")

            # 构建查询条件
            query = await self._build_query(conditions)

            # 🔥 添加数据源筛选
            query["source"] = source

            logger.info(f"📋 数据库查询条件: {query}")
            
            # 🔥 诊断：检查数据源中的股票总数
            total_stocks_in_source = await collection.count_documents({"source": source})
            logger.info(f"📊 数据源 {source} 共有 {total_stocks_in_source} 只股票")
            
            # 🔥 诊断：检查筛选条件是否包含行业筛选
            has_industry_filter = any(
                (isinstance(c, dict) and c.get("field") == "industry") or 
                (hasattr(c, "field") and c.field == "industry")
                for c in conditions
            )
            if has_industry_filter:
                # 检查该数据源有多少股票有行业信息
                stocks_with_industry = await collection.count_documents({
                    "source": source,
                    "$and": [
                        {"industry": {"$exists": True}},
                        {"industry": {"$ne": None}},
                        {"industry": {"$ne": ""}}
                    ]
                })
                logger.info(f"📊 数据源 {source} 中有 {stocks_with_industry} 只股票有行业信息")
                if stocks_with_industry == 0:
                    logger.warning(f"⚠️ 数据源 {source} 没有行业信息！如果筛选条件包含行业，将无法筛选出任何股票。建议：1) 使用 Tushare 数据源同步 2) 或移除行业筛选条件")

            # 构建排序条件
            sort_conditions = self._build_sort_conditions(order_by)

            # 获取总数
            total_count = await collection.count_documents(query)
            
            logger.info(f"📊 筛选结果: 符合条件的有 {total_count} 只股票（数据源: {source}）")

            # 执行查询
            cursor = collection.find(query)

            # 应用排序
            if sort_conditions:
                cursor = cursor.sort(sort_conditions)

            # 应用分页
            cursor = cursor.skip(offset).limit(limit)

            # 获取结果
            results = []
            codes = []
            async for doc in cursor:
                # 转换结果格式
                result = self._format_result(doc)
                results.append(result)
                codes.append(doc.get("code"))

            # 批量查询财务数据（ROE等）
            if codes:
                await self._enrich_with_financial_data(results, codes)

            logger.info(f"✅ 数据库筛选完成: 总数={total_count}, 返回={len(results)}, 数据源={source}")

            return results, total_count
            
        except Exception as e:
            logger.error(f"❌ 数据库筛选失败: {e}")
            raise Exception(f"数据库筛选失败: {str(e)}")
    
    async def _build_query(self, conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建MongoDB查询条件"""
        query = {}
        
        for condition in conditions:
            field = condition.get("field") if isinstance(condition, dict) else condition.field
            operator = condition.get("operator") if isinstance(condition, dict) else condition.operator
            value = condition.get("value") if isinstance(condition, dict) else condition.value
            
            # 映射字段名
            db_field = self.basic_fields.get(field)
            if not db_field:
                continue
            
            # 处理不同操作符
            if operator == "between":
                # between操作需要两个值
                if isinstance(value, list) and len(value) == 2:
                    query[db_field] = {
                        "$gte": value[0],
                        "$lte": value[1]
                    }
            elif operator == "contains":
                # 字符串包含（不区分大小写）
                query[db_field] = {
                    "$regex": str(value),
                    "$options": "i"
                }
            elif operator in self.operators:
                # 标准操作符
                mongo_op = self.operators[operator]
                query[db_field] = {mongo_op: value}
            
        return query
    
    def _build_sort_conditions(self, order_by: Optional[List[Dict[str, str]]]) -> List[Tuple[str, int]]:
        """构建排序条件"""
        if not order_by:
            # 默认按总市值降序排序
            return [("total_mv", -1)]
        
        sort_conditions = []
        for order in order_by:
            field = order.get("field")
            direction = order.get("direction", "desc")
            
            # 映射字段名
            db_field = self.basic_fields.get(field)
            if not db_field:
                continue
            
            # 映射排序方向
            sort_direction = -1 if direction.lower() == "desc" else 1
            sort_conditions.append((db_field, sort_direction))
        
        return sort_conditions
    
    async def _enrich_with_financial_data(self, results: List[Dict[str, Any]], codes: List[str]) -> None:
        """
        批量查询财务数据并填充到结果中

        Args:
            results: 筛选结果列表
            codes: 股票代码列表
        """
        try:
            db = get_mongo_db()
            financial_collection = db['stock_financial_data']

            # 🔥 获取数据源优先级配置
            from app.core.unified_config import UnifiedConfigManager
            config = UnifiedConfigManager()
            data_source_configs = await config.get_data_source_configs_async()

            # 提取启用的数据源，按优先级排序
            enabled_sources = [
                ds.type.lower() for ds in data_source_configs
                if ds.enabled and ds.type.lower() in ['tushare', 'akshare', 'baostock']
            ]

            if not enabled_sources:
                enabled_sources = ['tushare', 'akshare', 'baostock']

            # 优先使用优先级最高的数据源
            preferred_source = enabled_sources[0] if enabled_sources else 'tushare'

            # 批量查询最新的财务数据
            # 按 code 分组，取每个 code 的最新一期数据（只查询优先级最高的数据源）
            pipeline = [
                {"$match": {"code": {"$in": codes}, "data_source": preferred_source}},
                {"$sort": {"code": 1, "report_period": -1}},
                {"$group": {
                    "_id": "$code",
                    "roe": {"$first": "$roe"},
                    "roa": {"$first": "$roa"},
                    "netprofit_margin": {"$first": "$netprofit_margin"},
                    "gross_margin": {"$first": "$gross_margin"},
                }}
            ]

            financial_data_map = {}
            async for doc in financial_collection.aggregate(pipeline):
                code = doc.get("_id")
                financial_data_map[code] = {
                    "roe": doc.get("roe"),
                    "roa": doc.get("roa"),
                    "netprofit_margin": doc.get("netprofit_margin"),
                    "gross_margin": doc.get("gross_margin"),
                }

            # 填充财务数据到结果中
            for result in results:
                code = result.get("code")
                if code in financial_data_map:
                    financial_data = financial_data_map[code]
                    # 🔥 只更新 ROE（如果 stock_basic_info 中没有的话）
                    # 确保 ROE 是数值类型，不是字符串或其他类型
                    roe_value = financial_data.get("roe")
                    if roe_value is not None:
                        try:
                            # 确保是数值类型
                            roe_float = float(roe_value)
                            # 验证 ROE 的合理范围（通常在 -100% 到 100% 之间）
                            if -200 <= roe_float <= 200:
                                if result.get("roe") is None:
                                    result["roe"] = roe_float
                            else:
                                logger.warning(f"⚠️ 股票 {code} 的 ROE 值异常: {roe_float}，跳过填充")
                        except (ValueError, TypeError):
                            logger.warning(f"⚠️ 股票 {code} 的 ROE 值格式错误: {roe_value}，跳过填充")
                    # 可以添加更多财务指标
                    # result["roa"] = financial_data.get("roa")
                    # result["netprofit_margin"] = financial_data.get("netprofit_margin")

            logger.debug(f"✅ 已填充 {len(financial_data_map)} 条财务数据")

        except Exception as e:
            logger.warning(f"⚠️ 填充财务数据失败: {e}")
            # 不抛出异常，允许继续返回基础数据

    def _format_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """格式化查询结果，统一使用后端字段名"""
        # 根据股票代码推断市场类型
        code = doc.get("code", "")
        market_type = "A股"  # 默认A股
        if code:
            if code.startswith("6"):
                market_type = "A股"  # 上海
            elif code.startswith(("0", "3")):
                market_type = "A股"  # 深圳
            elif code.startswith("8") or code.startswith("4"):
                market_type = "A股"  # 北交所

        # 🔥 正确提取板块和交易所信息
        # 板块：优先使用数据库中的 board 字段，如果没有则使用 market 字段（market 存储的是板块信息）
        board_value = doc.get("board") or doc.get("market") or ""
        # 如果 board 字段是交易所名称（错误映射），则使用 market 字段
        if board_value in ["上海证券交易所", "深圳证券交易所", "北京证券交易所", "SSE", "SZSE", "BSE"]:
            board_value = doc.get("market") or ""
        
        # 交易所：优先使用 sse 字段，如果没有则根据股票代码推断
        exchange_value = doc.get("sse") or ""
        if not exchange_value:
            # 根据股票代码推断交易所
            if code.startswith(("60", "68", "90")):
                exchange_value = "上海证券交易所"
            elif code.startswith(("00", "30", "20")):
                exchange_value = "深圳证券交易所"
            elif code.startswith(("8", "4")):
                exchange_value = "北京证券交易所"

        result = {
            # 基础信息
            "code": doc.get("code"),
            "name": doc.get("name"),
            "industry": doc.get("industry"),
            "area": doc.get("area"),
            "market": market_type,  # 市场类型（A股、美股、港股）
            "board": board_value,  # 板块（主板、创业板、科创板等）
            "exchange": exchange_value,  # 交易所（上海证券交易所、深圳证券交易所等）
            "list_date": doc.get("list_date"),

            # 市值信息（亿元）
            "total_mv": doc.get("total_mv"),
            "circ_mv": doc.get("circ_mv"),

            # 财务指标（确保字段类型正确）
            "pe": self._safe_float(doc.get("pe")),
            "pb": self._safe_float(doc.get("pb")),
            "pe_ttm": self._safe_float(doc.get("pe_ttm")),
            "pb_mrq": self._safe_float(doc.get("pb_mrq")),
            "roe": self._safe_float(doc.get("roe")),  # 🔥 确保 ROE 是数值类型，不是字符串

            # 交易指标
            "turnover_rate": doc.get("turnover_rate"),
            "volume_ratio": doc.get("volume_ratio"),

            # 交易数据（基础信息筛选时为None，需要实时数据）
            "close": None,                          # 收盘价
            "pct_chg": None,                        # 涨跌幅(%)
            "amount": None,                         # 成交额

            # 技术指标（基础信息筛选时为None）
            "ma20": None,
            "rsi14": None,
            "kdj_k": None,
            "kdj_d": None,
            "kdj_j": None,
            "dif": None,
            "dea": None,
            "macd_hist": None,

            # 元数据
            "source": doc.get("source", "database"),
            "updated_at": doc.get("updated_at"),
        }
        
        # 🔥 添加字段验证和日志（用于调试字段错位问题）
        if code:
            # 验证关键字段类型
            if result.get("roe") is not None and not isinstance(result.get("roe"), (int, float)):
                logger.warning(f"⚠️ 股票 {code} 的 ROE 字段类型错误: {type(result.get('roe'))}, 值: {result.get('roe')}")
                # 尝试修复：如果是字符串且看起来像板块名称，则清空
                roe_val = result.get("roe")
                if isinstance(roe_val, str) and roe_val in ["主板", "创业板", "科创板", "中小板", "北交所"]:
                    logger.warning(f"⚠️ 股票 {code} 的 ROE 字段被错误地填充了板块信息: {roe_val}，已清空")
                    result["roe"] = None
            
            if result.get("board") is not None and isinstance(result.get("board"), (int, float)):
                logger.warning(f"⚠️ 股票 {code} 的 board 字段类型错误: {type(result.get('board'))}, 值: {result.get('board')}")
            
            if result.get("exchange") is not None and isinstance(result.get("exchange"), (int, float)):
                logger.warning(f"⚠️ 股票 {code} 的 exchange 字段类型错误: {type(result.get('exchange'))}, 值: {result.get('exchange')}")
        
        # 移除None值（但保留空字符串，因为某些字段可能为空字符串）
        return {k: v for k, v in result.items() if v is not None}
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """
        安全地将值转换为浮点数
        
        Args:
            value: 要转换的值
            
        Returns:
            float 或 None
        """
        if value is None:
            return None
        
        # 如果是字符串，检查是否是板块或交易所名称
        if isinstance(value, str):
            # 如果是板块或交易所名称，返回 None
            if value in ["主板", "创业板", "科创板", "中小板", "北交所", 
                        "上海证券交易所", "深圳证券交易所", "北京证券交易所",
                        "SSE", "SZSE", "BSE"]:
                return None
            # 尝试转换为浮点数
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # 如果是数值类型
        if isinstance(value, (int, float)):
            # 检查是否是 NaN 或 Inf
            if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
                return None
            return float(value)
        
        return None
    
    async def get_field_statistics(self, field: str) -> Dict[str, Any]:
        """
        获取字段的统计信息
        
        Args:
            field: 字段名
            
        Returns:
            Dict: 统计信息 {min, max, avg, count}
        """
        try:
            db_field = self.basic_fields.get(field)
            if not db_field:
                return {}
            
            db = get_mongo_db()
            collection = db[self.collection_name]
            
            # 使用聚合管道获取统计信息
            pipeline = [
                {"$match": {db_field: {"$exists": True, "$ne": None}}},
                {"$group": {
                    "_id": None,
                    "min": {"$min": f"${db_field}"},
                    "max": {"$max": f"${db_field}"},
                    "avg": {"$avg": f"${db_field}"},
                    "count": {"$sum": 1}
                }}
            ]
            
            result = await collection.aggregate(pipeline).to_list(length=1)
            
            if result:
                stats = result[0]
                avg_value = stats.get("avg")
                return {
                    "field": field,
                    "min": stats.get("min"),
                    "max": stats.get("max"),
                    "avg": round(avg_value, 2) if avg_value is not None else None,
                    "count": stats.get("count", 0)
                }
            
            return {"field": field, "count": 0}
            
        except Exception as e:
            logger.error(f"获取字段统计失败: {e}")
            return {"field": field, "error": str(e)}
    
    async def get_available_values(self, field: str, limit: int = 100) -> List[str]:
        """
        获取字段的可选值列表（用于枚举类型字段）
        
        Args:
            field: 字段名
            limit: 返回数量限制
            
        Returns:
            List[str]: 可选值列表
        """
        try:
            db_field = self.basic_fields.get(field)
            if not db_field:
                return []
            
            db = get_mongo_db()
            collection = db[self.collection_name]
            
            # 获取字段的不重复值
            values = await collection.distinct(db_field)
            
            # 过滤None值并排序
            values = [v for v in values if v is not None]
            values.sort()
            
            return values[:limit]
            
        except Exception as e:
            logger.error(f"获取字段可选值失败: {e}")
            return []


# 全局服务实例
_database_screening_service: Optional[DatabaseScreeningService] = None


def get_database_screening_service() -> DatabaseScreeningService:
    """获取数据库筛选服务实例"""
    global _database_screening_service
    if _database_screening_service is None:
        _database_screening_service = DatabaseScreeningService()
    return _database_screening_service
