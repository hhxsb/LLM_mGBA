#!/usr/bin/env python3
"""
Graphiti-based memory system for AI GBA Player.
Provides autonomous objective discovery, achievement tracking, and strategy learning.
"""

import os
import json
import time
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from graphiti_core import Graphiti
    from neo4j import GraphDatabase
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    logging.warning("Graphiti not available. Install with: pip install graphiti-core neo4j")


@dataclass
class GameObjective:
    """Represents a discovered game objective"""
    id: str
    description: str
    discovered_at: float
    completed_at: Optional[float] = None
    location_discovered: Optional[str] = None
    priority: int = 5  # 1-10 scale
    category: str = "general"  # "main", "side", "exploration", "collection"
    prerequisites: List[str] = None
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []


@dataclass
class GameAchievement:
    """Represents a completed achievement"""
    id: str
    title: str
    description: str
    completed_at: float
    location_completed: Optional[str] = None
    prerequisites_met: List[str] = None
    
    def __post_init__(self):
        if self.prerequisites_met is None:
            self.prerequisites_met = []


@dataclass
class GameStrategy:
    """Represents a learned strategy or pattern"""
    id: str
    situation_description: str
    button_sequence: List[str]
    success_rate: float
    times_used: int
    last_used: float
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


class GraphitiMemorySystem:
    """
    Advanced memory system using Graphiti for autonomous learning.
    Tracks objectives, achievements, and strategies as the AI plays.
    """
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", 
                 neo4j_user: str = "neo4j", neo4j_password: str = "password",
                 api_key: str = None, llm_provider: str = "google",
                 graphiti_config: dict = None):
        self.logger = logging.getLogger(__name__)
        
        if not GRAPHITI_AVAILABLE:
            raise ImportError("Graphiti is not installed. Install with: pip install graphiti-core neo4j")
        
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.api_key = api_key
        self.llm_provider = llm_provider
        
        # Default Graphiti configuration
        default_graphiti_config = {
            'llm_model': 'gemini-2.0-flash',
            'embedding_model': 'embedding-001',
            'reranker_model': 'gemini-2.5-flash-lite-preview-06-17'
        }
        self.graphiti_config = {**default_graphiti_config, **(graphiti_config or {})}
        
        # Initialize Graphiti client
        try:
            # Validate API key
            if not api_key:
                self.logger.warning(f"⚠️ No API key provided for {llm_provider} - Graphiti requires an API key")
                self.graphiti = None
                return
            
            # Initialize Graphiti with multi-provider support (updated for v0.20.2+)
            if llm_provider in ['google', 'gemini']:
                from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
                from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
                from graphiti_core.cross_encoder.gemini_reranker_client import GeminiRerankerClient
                
                # Create LLM client with configuration
                llm_config = LLMConfig(
                    api_key=api_key,
                    model=self.graphiti_config['llm_model']
                )
                llm_client = GeminiClient(config=llm_config)
                
                # Create embedder with configuration
                embedder_config = GeminiEmbedderConfig(
                    api_key=api_key,
                    embedding_model=self.graphiti_config['embedding_model']
                )
                embedder = GeminiEmbedder(config=embedder_config)
                
                # Create reranker with configuration
                reranker_config = LLMConfig(
                    api_key=api_key,
                    model=self.graphiti_config['reranker_model']
                )
                reranker = GeminiRerankerClient(config=reranker_config)
                
                # Initialize Graphiti with Gemini components
                self.graphiti = Graphiti(
                    uri=neo4j_uri,
                    user=neo4j_user,
                    password=neo4j_password,
                    llm_client=llm_client,
                    embedder=embedder,
                    cross_encoder=reranker
                )
                self.logger.info(f"✅ Graphiti memory system initialized with Google Gemini ({self.graphiti_config['llm_model']})")
                
            elif llm_provider == 'openai':
                # Set OpenAI API key in environment for Graphiti's automatic initialization
                import os
                os.environ['OPENAI_API_KEY'] = api_key
                
                # Initialize Graphiti with default OpenAI clients
                self.graphiti = Graphiti(
                    uri=neo4j_uri,
                    user=neo4j_user,
                    password=neo4j_password
                )
                self.logger.info(f"✅ Graphiti memory system initialized with OpenAI")
                
            elif llm_provider == 'anthropic':
                # Anthropic support would need custom client implementation
                self.logger.warning(f"⚠️ Anthropic not yet supported in this Graphiti version - falling back to SimpleMemorySystem")
                self.graphiti = None
                return
                
            else:
                raise ValueError(f"Unsupported LLM provider: {llm_provider}")
                
        except ImportError as e:
            self.logger.error(f"❌ Failed to import Graphiti components for {llm_provider}: {e}")
            self.graphiti = None
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Graphiti with {llm_provider}: {e}")
            self.graphiti = None
        
        # In-memory caches for performance
        self.active_objectives: Dict[str, GameObjective] = {}
        self.completed_achievements: Dict[str, GameAchievement] = {}
        self.learned_strategies: Dict[str, GameStrategy] = {}
        
        # Load existing data from Graphiti (skip for now due to async requirements)
        # TODO: Implement proper async knowledge loading
        # self._load_existing_knowledge()
    
    def _load_existing_knowledge(self):
        """Load existing objectives, achievements, and strategies from Graphiti"""
        if not self.graphiti:
            return
        
        try:
            # Query for existing objectives
            objectives_query = """
            MATCH (obj:Objective)
            RETURN obj.id as id, obj.description as description, 
                   obj.discovered_at as discovered_at, obj.completed_at as completed_at,
                   obj.location_discovered as location_discovered, obj.priority as priority,
                   obj.category as category
            """
            
            # Query for achievements
            achievements_query = """
            MATCH (ach:Achievement)
            RETURN ach.id as id, ach.title as title, ach.description as description,
                   ach.completed_at as completed_at, ach.location_completed as location_completed
            """
            
            # Query for strategies
            strategies_query = """
            MATCH (strat:Strategy)
            RETURN strat.id as id, strat.situation_description as situation_description,
                   strat.button_sequence as button_sequence, strat.success_rate as success_rate,
                   strat.times_used as times_used, strat.last_used as last_used
            """
            
            # Load objectives
            results = self.graphiti.search(objectives_query)
            for record in results.get('records', []):
                obj = GameObjective(
                    id=record['id'],
                    description=record['description'],
                    discovered_at=record['discovered_at'],
                    completed_at=record.get('completed_at'),
                    location_discovered=record.get('location_discovered'),
                    priority=record.get('priority', 5),
                    category=record.get('category', 'general')
                )
                if not obj.completed_at:  # Only keep active objectives
                    self.active_objectives[obj.id] = obj
            
            self.logger.info(f"📚 Loaded {len(self.active_objectives)} active objectives")
            
        except Exception as e:
            self.logger.error(f"❌ Error loading existing knowledge: {e}")
    
    def discover_objective(self, description: str, location: Optional[str] = None, 
                          category: str = "general", priority: int = 5, context: Dict[str, Any] = None) -> str:
        """
        Discover a new objective with rich context and temporal tracking.
        Returns the objective ID.
        """
        if not self.graphiti:
            return ""
        
        objective_id = f"obj_{int(time.time())}_{hash(description) % 10000}"
        current_time = time.time()
        context = context or {}
        
        objective = GameObjective(
            id=objective_id,
            description=description,
            discovered_at=current_time,
            location_discovered=location,
            category=category,
            priority=priority
        )
        
        try:
            # Enhanced episode with temporal context and relationships
            entities = [
                {
                    "entity_type": "Objective",
                    "entity_id": objective_id,
                    "description": description,
                    "discovered_at": current_time,
                    "location_discovered": location or "unknown",
                    "category": category,
                    "priority": priority,
                    "status": "active",
                    "game_session": context.get("session_id", "unknown"),
                    "player_level": context.get("player_level", 0),
                    "game_time": context.get("game_time", 0)
                }
            ]
            
            # Add location entity if provided
            if location:
                entities.append({
                    "entity_type": "Location",
                    "entity_id": f"loc_{location.replace(' ', '_').lower()}",
                    "name": location,
                    "first_visited": current_time,
                    "visit_count": context.get("visit_count", 1)
                })
            
            # Add relationships if context provided
            relationships = []
            if location:
                relationships.append({
                    "from": objective_id,
                    "to": f"loc_{location.replace(' ', '_').lower()}",
                    "relation": "discovered_at",
                    "strength": priority / 10.0
                })
            
            self.graphiti.add_episode(
                episode_id=f"discovery_{objective_id}",
                entities=entities,
                relationships=relationships,
                content=f"Discovered new objective: {description} at {location or 'unknown location'}. Priority: {priority}/10. Context: {context}"
            )
            
            # Add to local cache
            self.active_objectives[objective_id] = objective
            
            self.logger.info(f"🎯 Discovered objective: {description} (temporal context: {context})")
            return objective_id
            
        except Exception as e:
            self.logger.error(f"❌ Error discovering objective: {e}")
            return ""
    
    def complete_objective(self, objective_id: str, location: Optional[str] = None) -> bool:
        """
        Mark an objective as completed.
        Returns True if successful.
        """
        if not self.graphiti or objective_id not in self.active_objectives:
            return False
        
        objective = self.active_objectives[objective_id]
        current_time = time.time()
        
        try:
            # Update in Graphiti
            episode_data = {
                "entity_type": "ObjectiveCompletion",
                "entity_id": f"{objective_id}_completion",
                "objective_id": objective_id,
                "completed_at": current_time,
                "location_completed": location or "unknown"
            }
            
            self.graphiti.add_episode(
                episode_id=f"completion_{objective_id}",
                entities=[episode_data],
                content=f"Completed objective: {objective.description}"
            )
            
            # Move to achievements
            achievement = GameAchievement(
                id=objective_id,
                title=objective.description,
                description=f"Completed: {objective.description}",
                completed_at=current_time,
                location_completed=location
            )
            
            self.completed_achievements[objective_id] = achievement
            del self.active_objectives[objective_id]
            
            self.logger.info(f"✅ Completed objective: {objective.description}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error completing objective: {e}")
            return False
    
    def learn_strategy(self, situation: str, button_sequence: List[str], 
                      success: bool, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Learn a new strategy with enhanced temporal tracking and relationships.
        Returns the strategy ID.
        """
        if not self.graphiti:
            return ""
        
        strategy_id = f"strat_{hash(situation) % 10000}"
        current_time = time.time()
        context = context or {}
        
        if strategy_id in self.learned_strategies:
            # Update existing strategy
            strategy = self.learned_strategies[strategy_id]
            strategy.times_used += 1
            strategy.last_used = current_time
            
            # Update success rate
            if success:
                strategy.success_rate = (strategy.success_rate * (strategy.times_used - 1) + 1.0) / strategy.times_used
            else:
                strategy.success_rate = (strategy.success_rate * (strategy.times_used - 1)) / strategy.times_used
        else:
            # Create new strategy
            strategy = GameStrategy(
                id=strategy_id,
                situation_description=situation,
                button_sequence=button_sequence,
                success_rate=1.0 if success else 0.0,
                times_used=1,
                last_used=current_time,
                context=context
            )
            self.learned_strategies[strategy_id] = strategy
        
        try:
            # Enhanced episode with relationships and temporal context
            entities = [
                {
                    "entity_type": "Strategy",
                    "entity_id": strategy_id,
                    "situation_description": situation,
                    "button_sequence": json.dumps(button_sequence),
                    "success_rate": strategy.success_rate,
                    "times_used": strategy.times_used,
                    "last_used": current_time,
                    "success": success,
                    "location": context.get("location", "unknown"),
                    "game_state": context.get("game_state", "unknown"),
                    "session_id": context.get("session_id", "unknown")
                }
            ]
            
            # Add location entity if available
            location = context.get("location")
            if location:
                entities.append({
                    "entity_type": "Location",
                    "entity_id": f"loc_{location.replace(' ', '_').lower()}",
                    "name": location,
                    "strategy_success_rate": strategy.success_rate
                })
            
            # Add game state entity for pattern recognition
            game_state = context.get("game_state")
            if game_state:
                entities.append({
                    "entity_type": "GameState",
                    "entity_id": f"state_{hash(game_state) % 10000}",
                    "description": game_state,
                    "timestamp": current_time
                })
            
            # Build relationships
            relationships = []
            if location:
                relationships.append({
                    "from": strategy_id,
                    "to": f"loc_{location.replace(' ', '_').lower()}",
                    "relation": "used_at",
                    "strength": strategy.success_rate,
                    "temporal_validity": [current_time, None]  # Valid from now
                })
            
            if game_state:
                relationships.append({
                    "from": strategy_id,
                    "to": f"state_{hash(game_state) % 10000}",
                    "relation": "effective_in",
                    "strength": 1.0 if success else 0.0
                })
            
            self.graphiti.add_episode(
                episode_id=f"strategy_{strategy_id}_{int(current_time)}",
                entities=entities,
                relationships=relationships,
                content=f"{'Successful' if success else 'Failed'} strategy for: {situation}. Buttons: {button_sequence}. Location: {location or 'unknown'}. Success rate now: {strategy.success_rate:.2%}"
            )
            
            self.logger.info(f"🧠 {'Updated' if strategy.times_used > 1 else 'Learned'} strategy: {situation} (success: {strategy.success_rate:.1%})")
            return strategy_id
            
        except Exception as e:
            self.logger.error(f"❌ Error learning strategy: {e}")
            return ""
    
    def get_current_objectives(self, category: Optional[str] = None, max_count: int = 5) -> List[GameObjective]:
        """Get current active objectives, optionally filtered by category"""
        objectives = list(self.active_objectives.values())
        
        if category:
            objectives = [obj for obj in objectives if obj.category == category]
        
        # Sort by priority (higher first) and discovery time
        objectives.sort(key=lambda x: (-x.priority, x.discovered_at))
        
        return objectives[:max_count]
    
    def get_relevant_strategies(self, situation: str, min_success_rate: float = 0.5) -> List[GameStrategy]:
        """Get strategies relevant to the current situation"""
        relevant_strategies = []
        
        for strategy in self.learned_strategies.values():
            # Simple keyword matching for now - could be enhanced with embeddings
            if (any(word in strategy.situation_description.lower() for word in situation.lower().split()) and
                strategy.success_rate >= min_success_rate):
                relevant_strategies.append(strategy)
        
        # Sort by success rate and recency
        relevant_strategies.sort(key=lambda x: (-x.success_rate, -x.last_used))
        
        return relevant_strategies[:3]  # Top 3 strategies
    
    def get_memory_context(self, current_situation: str = "", max_objectives: int = 3, 
                          location: str = None) -> Dict[str, Any]:
        """
        Get enhanced memory context using semantic search and temporal analysis.
        """
        context = {
            "current_objectives": [],
            "recent_achievements": [],
            "relevant_strategies": [],
            "location_insights": {},
            "pokemon_knowledge": {},
            "temporal_patterns": {},
            "discovery_suggestions": []
        }
        
        # Current objectives with enhanced context
        objectives = self.get_current_objectives(max_count=max_objectives)
        context["current_objectives"] = [
            {
                "description": obj.description,
                "priority": obj.priority,
                "category": obj.category,
                "location_discovered": obj.location_discovered,
                "time_since_discovery": self._describe_age(time.time() - obj.discovered_at)
            }
            for obj in objectives
        ]
        
        # Recent achievements with temporal context
        recent_achievements = sorted(
            self.completed_achievements.values(),
            key=lambda x: x.completed_at,
            reverse=True
        )[:5]
        
        context["recent_achievements"] = [
            {
                "title": ach.title,
                "completed_at": datetime.fromtimestamp(ach.completed_at).strftime("%Y-%m-%d %H:%M"),
                "location": ach.location_completed,
                "time_ago": self._describe_age(time.time() - ach.completed_at)
            }
            for ach in recent_achievements
        ]
        
        # Enhanced strategy retrieval with semantic search
        if current_situation:
            # Use semantic search if Graphiti is available
            if self.graphiti:
                try:
                    # Query for semantically similar situations
                    strategy_query = f"successful strategies for situation similar to: {current_situation}"
                    semantic_results = self.query_knowledge(strategy_query, include_temporal=True)
                    
                    # Combine with local strategy matching
                    local_strategies = self.get_relevant_strategies(current_situation)
                    
                    # Process and merge results
                    context["relevant_strategies"] = self._merge_strategy_results(
                        local_strategies, semantic_results.get("results", [])
                    )
                    
                    # Add temporal patterns from semantic search
                    context["temporal_patterns"] = semantic_results.get("temporal_analysis", {})
                    
                except Exception as e:
                    self.logger.debug(f"Semantic search failed, using local strategies: {e}")
                    context["relevant_strategies"] = self._format_local_strategies(
                        self.get_relevant_strategies(current_situation)
                    )
            else:
                context["relevant_strategies"] = self._format_local_strategies(
                    self.get_relevant_strategies(current_situation)
                )
        
        # Location-specific insights
        if location and self.graphiti:
            try:
                location_query = f"information about location {location} including Pokemon and strategies"
                location_results = self.query_knowledge(location_query, include_temporal=False)
                context["location_insights"] = self._extract_location_insights(location_results)
            except Exception as e:
                self.logger.debug(f"Location insights failed: {e}")
        
        # Pokemon knowledge for current area
        if self.graphiti:
            try:
                pokemon_query = f"Pokemon encounters and battle strategies {f'at {location}' if location else ''}"
                pokemon_results = self.query_knowledge(pokemon_query, include_temporal=True)
                context["pokemon_knowledge"] = self._extract_pokemon_insights(pokemon_results)
            except Exception as e:
                self.logger.debug(f"Pokemon knowledge query failed: {e}")
        
        # Enhanced discovery suggestions based on context
        context["discovery_suggestions"] = self._generate_contextual_suggestions(
            current_situation, location, context
        )
        
        return context
    
    def _merge_strategy_results(self, local_strategies: List[GameStrategy], 
                               semantic_results: List[Dict]) -> List[Dict[str, Any]]:
        """Merge local strategies with semantic search results"""
        merged = []
        
        # Add local strategies first (they're already filtered for relevance)
        for strat in local_strategies:
            merged.append({
                "situation": strat.situation_description,
                "buttons": strat.button_sequence,
                "success_rate": f"{strat.success_rate:.1%}",
                "times_used": strat.times_used,
                "source": "local_memory",
                "recency_score": getattr(strat, 'recency_score', 0.5)
            })
        
        # Add semantic results if they're not duplicates
        for result in semantic_results[:3]:  # Limit semantic results
            if not any(result.get('situation_description', '') in s['situation'] for s in merged):
                merged.append({
                    "situation": result.get('situation_description', 'Unknown'),
                    "buttons": result.get('button_sequence', []),
                    "success_rate": f"{result.get('success_rate', 0):.1%}",
                    "times_used": result.get('times_used', 0),
                    "source": "semantic_search",
                    "recency_score": result.get('recency_score', 0.3)
                })
        
        # Sort by success rate and recency
        merged.sort(key=lambda x: (float(x['success_rate'].rstrip('%')) / 100, x['recency_score']), reverse=True)
        return merged[:5]  # Top 5 strategies
    
    def _format_local_strategies(self, strategies: List[GameStrategy]) -> List[Dict[str, Any]]:
        """Format local strategies for context"""
        return [
            {
                "situation": strat.situation_description,
                "buttons": strat.button_sequence,
                "success_rate": f"{strat.success_rate:.1%}",
                "times_used": strat.times_used,
                "source": "local_memory"
            }
            for strat in strategies
        ]
    
    def _extract_location_insights(self, location_results: Dict) -> Dict[str, Any]:
        """Extract location-specific insights from search results"""
        insights = {
            "pokemon_found": [],
            "success_strategies": [],
            "visit_frequency": "unknown"
        }
        
        results = location_results.get("results", [])
        for result in results:
            if result.get("entity_type") == "Pokemon":
                insights["pokemon_found"].append({
                    "name": result.get("name", "Unknown"),
                    "frequency": result.get("frequency", 1)
                })
            elif result.get("entity_type") == "Strategy":
                if result.get("success_rate", 0) > 0.7:
                    insights["success_strategies"].append({
                        "situation": result.get("situation_description", ""),
                        "success_rate": result.get("success_rate", 0)
                    })
        
        return insights
    
    def _extract_pokemon_insights(self, pokemon_results: Dict) -> Dict[str, Any]:
        """Extract Pokemon-related insights"""
        insights = {
            "recently_encountered": [],
            "battle_strategies": [],
            "catch_patterns": {}
        }
        
        results = pokemon_results.get("results", [])
        for result in results:
            if result.get("entity_type") == "Encounter":
                insights["recently_encountered"].append({
                    "pokemon": result.get("pokemon_name", "Unknown"),
                    "location": result.get("location", "Unknown"),
                    "time_ago": result.get("age_description", "Unknown")
                })
            elif result.get("entity_type") == "Battle":
                insights["battle_strategies"].append({
                    "opponent": result.get("opponent_type", "Unknown"),
                    "outcome": result.get("outcome", "Unknown"),
                    "strategy": result.get("strategy_used", "Unknown")
                })
        
        return insights
    
    def _generate_contextual_suggestions(self, situation: str, location: str, 
                                       context: Dict[str, Any]) -> List[str]:
        """Generate context-aware discovery suggestions"""
        suggestions = []
        
        # Base suggestions
        base_suggestions = [
            "Look for NPCs to talk to - they often provide objectives",
            "Check for items or interactable objects",
            "Notice location names and landmarks for navigation"
        ]
        
        # Add location-specific suggestions
        if location:
            suggestions.append(f"Explore thoroughly at {location} - check for hidden items or areas")
            
            # Check if we have Pokemon knowledge for this location
            location_pokemon = context.get("location_insights", {}).get("pokemon_found", [])
            if location_pokemon:
                suggestions.append(f"Pokemon spotted here: {', '.join([p['name'] for p in location_pokemon[:3]])}")
        
        # Add strategy-based suggestions
        strategies = context.get("relevant_strategies", [])
        if strategies:
            best_strategy = strategies[0]
            suggestions.append(f"Try proven strategy: {best_strategy['situation']} ({best_strategy['success_rate']} success)")
        
        # Add temporal suggestions
        patterns = context.get("temporal_patterns", {})
        if patterns.get("success_patterns"):
            suggestions.append("Recent successful patterns detected - check strategy list")
        
        return suggestions[:6]  # Limit to 6 suggestions
    
    def query_knowledge(self, query: str, include_temporal: bool = True) -> Dict[str, Any]:
        """
        Query the knowledge graph using natural language with temporal awareness.
        Returns relevant information with temporal context.
        """
        if not self.graphiti:
            return {"error": "Graphiti not available"}
        
        try:
            # Enhanced query with temporal context
            if include_temporal:
                current_time = time.time()
                temporal_query = f"{query} - considering temporal patterns and recent changes in the last hour"
                results = self.graphiti.search(temporal_query, limit=10)
            else:
                results = self.graphiti.search(query, limit=5)
            
            # Process results to extract temporal insights
            processed_results = self._process_temporal_results(results)
            
            return {
                "query": query,
                "results": processed_results,
                "temporal_analysis": self._analyze_temporal_patterns(query),
                "timestamp": time.time()
            }
        except Exception as e:
            self.logger.error(f"❌ Error querying knowledge: {e}")
            return {"error": str(e)}
    
    def _process_temporal_results(self, results) -> List[Dict[str, Any]]:
        """Process search results to include temporal insights"""
        processed = []
        current_time = time.time()
        
        for result in results.get('results', []):
            # Add temporal context to each result
            result_with_temporal = dict(result)
            
            # Calculate recency score
            if 'timestamp' in result:
                age_seconds = current_time - result['timestamp']
                age_hours = age_seconds / 3600
                result_with_temporal['recency_score'] = max(0, 1 - (age_hours / 24))  # Decay over 24 hours
                result_with_temporal['age_description'] = self._describe_age(age_seconds)
            
            processed.append(result_with_temporal)
        
        # Sort by relevance and recency
        processed.sort(key=lambda x: x.get('recency_score', 0), reverse=True)
        return processed
    
    def _analyze_temporal_patterns(self, query: str) -> Dict[str, Any]:
        """Analyze temporal patterns related to the query"""
        try:
            patterns = {
                "frequent_times": [],
                "recent_trends": [],
                "success_patterns": []
            }
            
            # Analyze strategy usage patterns over time
            if "strategy" in query.lower() or "how" in query.lower():
                for strategy in self.learned_strategies.values():
                    if strategy.success_rate > 0.7 and strategy.times_used > 2:
                        patterns["success_patterns"].append({
                            "strategy": strategy.situation_description,
                            "success_rate": strategy.success_rate,
                            "usage_frequency": strategy.times_used,
                            "last_successful": strategy.last_used
                        })
            
            return patterns
        except Exception as e:
            self.logger.error(f"Error analyzing temporal patterns: {e}")
            return {}
    
    def _describe_age(self, age_seconds: float) -> str:
        """Convert age in seconds to human-readable description"""
        if age_seconds < 60:
            return "just now"
        elif age_seconds < 3600:
            return f"{int(age_seconds // 60)} minutes ago"
        elif age_seconds < 86400:
            return f"{int(age_seconds // 3600)} hours ago"
        else:
            return f"{int(age_seconds // 86400)} days ago"
    
    def record_pokemon_encounter(self, pokemon_name: str, location: str, level: int = None, 
                                caught: bool = False, context: Dict[str, Any] = None) -> str:
        """
        Record a Pokemon encounter with rich relationship modeling.
        Returns the encounter ID.
        """
        if not self.graphiti:
            return ""
        
        encounter_id = f"encounter_{int(time.time())}_{hash(pokemon_name) % 10000}"
        current_time = time.time()
        context = context or {}
        
        try:
            # Create comprehensive entities
            entities = [
                {
                    "entity_type": "Pokemon",
                    "entity_id": f"pokemon_{pokemon_name.lower().replace(' ', '_')}",
                    "name": pokemon_name,
                    "species": pokemon_name,
                    "first_encountered": current_time,
                    "times_encountered": context.get("encounter_count", 1),
                    "caught": caught
                },
                {
                    "entity_type": "Encounter", 
                    "entity_id": encounter_id,
                    "pokemon_name": pokemon_name,
                    "location": location,
                    "level": level or "unknown",
                    "caught": caught,
                    "timestamp": current_time,
                    "weather": context.get("weather", "unknown"),
                    "time_of_day": context.get("time_of_day", "unknown")
                },
                {
                    "entity_type": "Location",
                    "entity_id": f"loc_{location.replace(' ', '_').lower()}",
                    "name": location,
                    "pokemon_species_count": context.get("species_count", 1),
                    "last_visited": current_time
                }
            ]
            
            # Build rich relationships
            relationships = [
                {
                    "from": encounter_id,
                    "to": f"pokemon_{pokemon_name.lower().replace(' ', '_')}",
                    "relation": "encountered_pokemon",
                    "strength": 1.0,
                    "properties": {"level": level, "caught": caught}
                },
                {
                    "from": encounter_id, 
                    "to": f"loc_{location.replace(' ', '_').lower()}",
                    "relation": "occurred_at",
                    "strength": 1.0,
                    "temporal_validity": [current_time, None]
                },
                {
                    "from": f"pokemon_{pokemon_name.lower().replace(' ', '_')}",
                    "to": f"loc_{location.replace(' ', '_').lower()}", 
                    "relation": "found_at",
                    "strength": context.get("encounter_count", 1) / 10.0,  # Stronger with more encounters
                    "properties": {"frequency": context.get("encounter_count", 1)}
                }
            ]
            
            # Add trainer relationship if caught
            if caught:
                relationships.append({
                    "from": "player",
                    "to": f"pokemon_{pokemon_name.lower().replace(' ', '_')}",
                    "relation": "owns",
                    "strength": 1.0,
                    "timestamp": current_time
                })
            
            self.graphiti.add_episode(
                episode_id=encounter_id,
                entities=entities,
                relationships=relationships,
                content=f"{'Caught' if caught else 'Encountered'} {pokemon_name} (Level {level}) at {location}. {context}"
            )
            
            self.logger.info(f"🎮 {'Caught' if caught else 'Encountered'} {pokemon_name} at {location}")
            return encounter_id
            
        except Exception as e:
            self.logger.error(f"❌ Error recording Pokemon encounter: {e}")
            return ""
    
    def record_battle_outcome(self, opponent_type: str, outcome: str, location: str, 
                             context: Dict[str, Any] = None) -> str:
        """
        Record battle outcomes with strategic analysis.
        Returns the battle ID.
        """
        if not self.graphiti:
            return ""
        
        battle_id = f"battle_{int(time.time())}_{hash(opponent_type) % 10000}"
        current_time = time.time()
        context = context or {}
        
        try:
            entities = [
                {
                    "entity_type": "Battle",
                    "entity_id": battle_id,
                    "opponent_type": opponent_type,
                    "outcome": outcome,  # "won", "lost", "fled"
                    "location": location,
                    "timestamp": current_time,
                    "player_team_size": context.get("team_size", 1),
                    "strategy_used": context.get("strategy", "unknown")
                },
                {
                    "entity_type": "Opponent",
                    "entity_id": f"opponent_{opponent_type.lower().replace(' ', '_')}",
                    "type": opponent_type,
                    "battles_fought": context.get("battles_against", 1),
                    "win_rate_against": context.get("win_rate", 1.0 if outcome == "won" else 0.0)
                }
            ]
            
            relationships = [
                {
                    "from": battle_id,
                    "to": f"loc_{location.replace(' ', '_').lower()}",
                    "relation": "fought_at",
                    "strength": 1.0
                },
                {
                    "from": "player",
                    "to": f"opponent_{opponent_type.lower().replace(' ', '_')}",
                    "relation": "battled",
                    "strength": 1.0 if outcome == "won" else 0.5,
                    "properties": {"outcome": outcome, "timestamp": current_time}
                }
            ]
            
            self.graphiti.add_episode(
                episode_id=battle_id,
                entities=entities,
                relationships=relationships,
                content=f"Battle against {opponent_type} at {location}: {outcome}. {context}"
            )
            
            self.logger.info(f"⚔️ Battle vs {opponent_type}: {outcome}")
            return battle_id
            
        except Exception as e:
            self.logger.error(f"❌ Error recording battle: {e}")
            return ""

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory system statistics"""
        stats = {
            "active_objectives": len(self.active_objectives),
            "completed_achievements": len(self.completed_achievements),
            "learned_strategies": len(self.learned_strategies),
            "total_strategy_uses": sum(s.times_used for s in self.learned_strategies.values()),
            "avg_strategy_success": sum(s.success_rate for s in self.learned_strategies.values()) / len(self.learned_strategies) if self.learned_strategies else 0
        }
        
        # Add temporal analysis
        if self.graphiti:
            try:
                # Query for recent activity
                recent_query = self.query_knowledge("recent activity in the last hour", include_temporal=True)
                stats["recent_activity_count"] = len(recent_query.get("results", []))
                stats["temporal_patterns"] = recent_query.get("temporal_analysis", {})
            except Exception as e:
                self.logger.debug(f"Could not get temporal stats: {e}")
        
        return stats


# Fallback memory system for when Graphiti is not available
class SimpleMemorySystem:
    """
    Simple in-memory fallback when Graphiti is not available.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.warning("⚠️ Using simple memory system - Graphiti not available")
        
        self.objectives: Dict[str, Dict] = {}
        self.achievements: List[Dict] = []
        self.strategies: Dict[str, Dict] = {}
    
    def discover_objective(self, description: str, location: Optional[str] = None, 
                          category: str = "general", priority: int = 5) -> str:
        objective_id = f"obj_{int(time.time())}"
        self.objectives[objective_id] = {
            "description": description,
            "discovered_at": time.time(),
            "location": location,
            "category": category,
            "priority": priority
        }
        self.logger.info(f"🎯 Simple: Discovered objective: {description}")
        return objective_id
    
    def complete_objective(self, objective_id: str, location: Optional[str] = None) -> bool:
        if objective_id in self.objectives:
            obj = self.objectives.pop(objective_id)
            self.achievements.append({
                "title": obj["description"],
                "completed_at": time.time(),
                "location": location
            })
            self.logger.info(f"✅ Simple: Completed objective: {obj['description']}")
            return True
        return False
    
    def learn_strategy(self, situation: str, button_sequence: List[str], 
                      success: bool, context: Optional[Dict[str, Any]] = None) -> str:
        strategy_id = f"strat_{hash(situation) % 10000}"
        if strategy_id not in self.strategies:
            self.strategies[strategy_id] = {
                "situation": situation,
                "buttons": button_sequence,
                "success_count": 0,
                "total_count": 0
            }
        
        self.strategies[strategy_id]["total_count"] += 1
        if success:
            self.strategies[strategy_id]["success_count"] += 1
        
        return strategy_id
    
    def get_memory_context(self, current_situation: str = "", max_objectives: int = 3) -> Dict[str, Any]:
        return {
            "current_objectives": [
                {"description": obj["description"], "priority": obj["priority"]}
                for obj in list(self.objectives.values())[:max_objectives]
            ],
            "recent_achievements": self.achievements[-3:],
            "relevant_strategies": [],
            "discovery_suggestions": ["Simple memory system active - limited features"]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_objectives": len(self.objectives),
            "completed_achievements": len(self.achievements),
            "learned_strategies": len(self.strategies)
        }


def create_memory_system(system_type: str = 'auto',
                        api_key: str = None,
                        llm_provider: str = 'google',
                        neo4j_uri: str = "bolt://localhost:7687", 
                        neo4j_user: str = "neo4j", 
                        neo4j_password: str = "password",
                        graphiti_config: dict = None):
    """
    Enhanced factory function to create the appropriate memory system with multi-provider support.
    Returns GraphitiMemorySystem if available and configured, otherwise SimpleMemorySystem.
    """
    graphiti_config = graphiti_config or {}
    
    if system_type == 'simple':
        return SimpleMemorySystem()
    
    if system_type == 'graphiti' or (system_type == 'auto' and GRAPHITI_AVAILABLE):
        if not GRAPHITI_AVAILABLE:
            logging.warning("🔄 Graphiti requested but not available, falling back to simple memory system")
            return SimpleMemorySystem()
        
        try:
            memory_system = GraphitiMemorySystem(
                api_key=api_key,
                llm_provider=llm_provider,
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password,
                graphiti_config=graphiti_config
            )
            # Check if GraphitiMemorySystem successfully initialized
            if memory_system.graphiti is None:
                logging.info("🔄 Graphiti not fully initialized, falling back to simple memory system")
                return SimpleMemorySystem()
            return memory_system
        except Exception as e:
            logging.error(f"❌ Failed to create Graphiti memory system: {e}")
            logging.info("🔄 Falling back to simple memory system")
            return SimpleMemorySystem()
    else:
        return SimpleMemorySystem()