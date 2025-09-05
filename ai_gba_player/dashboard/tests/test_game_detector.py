from django.test import TestCase
from unittest.mock import patch, MagicMock
import re

from dashboard.game_detector import GameDetector, GameConfig, get_game_detector


class GameConfigTest(TestCase):
    """Test GameConfig dataclass functionality"""
    
    def test_game_config_creation(self):
        """Test GameConfig can be created with required fields"""
        config = GameConfig(
            id="test_game",
            name="Test Game",
            platform="Test Platform",
            memory_type="static",
            memory_addresses={"playerX": 0x1000},
            direction_encoding={1: "UP", 2: "DOWN"}
        )
        
        self.assertEqual(config.id, "test_game")
        self.assertEqual(config.name, "Test Game")
        self.assertEqual(config.platform, "Test Platform")
        self.assertEqual(config.memory_type, "static")
        self.assertEqual(config.memory_addresses["playerX"], 0x1000)
        self.assertEqual(config.direction_encoding[1], "UP")
        self.assertIsNone(config.fallback_addresses)
    
    def test_game_config_with_fallback_addresses(self):
        """Test GameConfig with fallback addresses"""
        fallback_addresses = [
            {"playerX": 0x1000, "playerY": 0x1002},
            {"playerX": 0x2000, "playerY": 0x2002}
        ]
        
        config = GameConfig(
            id="test_fallback",
            name="Test Fallback Game",
            platform="GBA",
            memory_type="dynamic",
            memory_addresses={},
            direction_encoding={},
            fallback_addresses=fallback_addresses
        )
        
        self.assertEqual(config.fallback_addresses, fallback_addresses)
        self.assertEqual(len(config.fallback_addresses), 2)
        self.assertEqual(config.fallback_addresses[0]["playerX"], 0x1000)


class GameDetectorInitializationTest(TestCase):
    """Test GameDetector initialization"""
    
    def test_detector_initialization(self):
        """Test GameDetector initializes with proper game configs"""
        detector = GameDetector()
        
        self.assertIsInstance(detector.games, dict)
        self.assertIsNone(detector.manual_override)
        
        # Test that expected games are loaded
        expected_games = [
            "pokemon_red", "pokemon_sapphire", "pokemon_ruby",
            "pokemon_emerald", "pokemon_firered", "pokemon_leafgreen"
        ]
        
        for game_id in expected_games:
            self.assertIn(game_id, detector.games)
            self.assertIsInstance(detector.games[game_id], GameConfig)
    
    def test_pokemon_red_config(self):
        """Test Pokemon Red/Blue configuration is correct"""
        detector = GameDetector()
        red_config = detector.games["pokemon_red"]
        
        self.assertEqual(red_config.id, "pokemon_red")
        self.assertEqual(red_config.name, "Pokémon Red/Blue")
        self.assertEqual(red_config.platform, "Game Boy")
        self.assertEqual(red_config.memory_type, "static")
        
        # Test memory addresses are properly set
        self.assertEqual(red_config.memory_addresses["playerDirection"], 0xC109)
        self.assertEqual(red_config.memory_addresses["playerX"], 0xD362)
        self.assertEqual(red_config.memory_addresses["playerY"], 0xD361)
        self.assertEqual(red_config.memory_addresses["mapId"], 0xD35E)
        
        # Test direction encoding
        self.assertEqual(red_config.direction_encoding[0], "DOWN")
        self.assertEqual(red_config.direction_encoding[4], "UP")
        self.assertEqual(red_config.direction_encoding[8], "LEFT")
        self.assertEqual(red_config.direction_encoding[12], "RIGHT")
    
    def test_pokemon_sapphire_config(self):
        """Test Pokemon Sapphire configuration is correct"""
        detector = GameDetector()
        sapphire_config = detector.games["pokemon_sapphire"]
        
        self.assertEqual(sapphire_config.id, "pokemon_sapphire")
        self.assertEqual(sapphire_config.name, "Pokémon Sapphire")
        self.assertEqual(sapphire_config.platform, "Game Boy Advance")
        self.assertEqual(sapphire_config.memory_type, "dynamic")
        
        # Test that memory addresses start as None (dynamic detection)
        for addr in sapphire_config.memory_addresses.values():
            self.assertIsNone(addr)
        
        # Test fallback addresses exist
        self.assertIsNotNone(sapphire_config.fallback_addresses)
        self.assertGreater(len(sapphire_config.fallback_addresses), 0)
        
        # Test direction encoding includes both standard and TBL
        self.assertEqual(sapphire_config.direction_encoding[1], "DOWN")
        self.assertEqual(sapphire_config.direction_encoding[0x79], "UP")  # TBL encoding
        self.assertEqual(sapphire_config.direction_encoding[0x7A], "DOWN")  # TBL encoding


class GameDetectorRomNameDetectionTest(TestCase):
    """Test ROM name detection functionality"""
    
    def setUp(self):
        self.detector = GameDetector()
    
    def test_detect_pokemon_sapphire(self):
        """Test Pokemon Sapphire detection from various ROM names"""
        test_names = [
            "Pokemon Sapphire",
            "POKEMON SAPPHIRE",
            "pokemon sapphire version",
            "Pokemon - Sapphire Version (U)",
            "POKEMON_SAPPHIRE_USA",
            "Pokemon Sapphire (E) [!]"
        ]
        
        for rom_name in test_names:
            with self.subTest(rom_name=rom_name):
                result = self.detector.detect_game_from_rom_name(rom_name)
                self.assertEqual(result, "pokemon_sapphire")
    
    def test_detect_pokemon_ruby(self):
        """Test Pokemon Ruby detection"""
        test_names = [
            "Pokemon Ruby",
            "POKEMON RUBY",
            "Pokemon - Ruby Version (U)",
            "POKEMON_RUBY_USA"
        ]
        
        for rom_name in test_names:
            with self.subTest(rom_name=rom_name):
                result = self.detector.detect_game_from_rom_name(rom_name)
                self.assertEqual(result, "pokemon_ruby")
    
    def test_detect_pokemon_emerald(self):
        """Test Pokemon Emerald detection"""
        test_names = [
            "Pokemon Emerald",
            "POKEMON EMERALD",
            "Pokemon - Emerald Version (U)",
            "POKEMON_EMERALD_USA"
        ]
        
        for rom_name in test_names:
            with self.subTest(rom_name=rom_name):
                result = self.detector.detect_game_from_rom_name(rom_name)
                self.assertEqual(result, "pokemon_emerald")
    
    def test_detect_pokemon_firered(self):
        """Test Pokemon FireRed detection"""
        test_names = [
            "Pokemon FireRed",
            "POKEMON FIRERED",
            "Pokemon - FireRed Version (U)",
            "POKEMON_FIRERED_USA"
        ]
        
        for rom_name in test_names:
            with self.subTest(rom_name=rom_name):
                result = self.detector.detect_game_from_rom_name(rom_name)
                self.assertEqual(result, "pokemon_firered")
    
    def test_detect_pokemon_leafgreen(self):
        """Test Pokemon LeafGreen detection"""
        test_names = [
            "Pokemon LeafGreen",
            "POKEMON LEAFGREEN",
            "Pokemon - LeafGreen Version (U)",
            "POKEMON_LEAFGREEN_USA"
        ]
        
        for rom_name in test_names:
            with self.subTest(rom_name=rom_name):
                result = self.detector.detect_game_from_rom_name(rom_name)
                self.assertEqual(result, "pokemon_leafgreen")
    
    def test_detect_pokemon_red_blue(self):
        """Test Pokemon Red/Blue detection"""
        test_names = [
            "Pokemon Red",
            "POKEMON RED",
            "Pokemon - Red Version (U)",
            "Pokemon Blue",
            "POKEMON BLUE",
            "Pokemon - Blue Version (U)"
        ]
        
        for rom_name in test_names:
            with self.subTest(rom_name=rom_name):
                result = self.detector.detect_game_from_rom_name(rom_name)
                self.assertEqual(result, "pokemon_red")  # Blue uses Red config
    
    def test_detection_priority_order(self):
        """Test that more specific patterns are matched first"""
        # FireRed should be detected before Red due to pattern order
        result = self.detector.detect_game_from_rom_name("Pokemon FireRed")
        self.assertEqual(result, "pokemon_firered")
        
        # LeafGreen should be detected before generic pattern
        result = self.detector.detect_game_from_rom_name("Pokemon LeafGreen")
        self.assertEqual(result, "pokemon_leafgreen")
    
    def test_detect_no_match(self):
        """Test detection returns None for unknown games"""
        test_names = [
            "Super Mario Bros",
            "Zelda",
            "Unknown Game",
            "Not A Pokemon Game",
            ""
        ]
        
        for rom_name in test_names:
            with self.subTest(rom_name=rom_name):
                result = self.detector.detect_game_from_rom_name(rom_name)
                self.assertIsNone(result)
    
    def test_detect_none_input(self):
        """Test detection handles None input gracefully"""
        result = self.detector.detect_game_from_rom_name(None)
        self.assertIsNone(result)


class GameDetectorPathDetectionTest(TestCase):
    """Test ROM path detection functionality"""
    
    def setUp(self):
        self.detector = GameDetector()
    
    def test_detect_from_path_with_extensions(self):
        """Test path detection with various file extensions"""
        test_paths = [
            "/roms/Pokemon Sapphire.gba",
            "/path/to/POKEMON RUBY.GBA",
            "/games/pokemon emerald.gbc",
            "C:\\Games\\Pokemon FireRed.zip",
            "/home/user/roms/Pokemon LeafGreen.7z"
        ]
        
        expected_results = [
            "pokemon_sapphire",
            "pokemon_ruby", 
            "pokemon_emerald",
            "pokemon_firered",
            "pokemon_leafgreen"
        ]
        
        for path, expected in zip(test_paths, expected_results):
            with self.subTest(path=path):
                result = self.detector.detect_game_from_path(path)
                self.assertEqual(result, expected)
    
    def test_detect_from_complex_paths(self):
        """Test detection from complex file paths"""
        complex_paths = [
            "/very/deep/directory/structure/Pokemon - Sapphire Version (U) [!].gba",
            "C:\\Users\\Gaming\\ROMs\\GBA\\Pokemon Ruby (USA).GBA",
            "/media/usb/games/backups/Pokemon Emerald v1.0.zip"
        ]
        
        expected_results = [
            "pokemon_sapphire",
            "pokemon_ruby",
            "pokemon_emerald"
        ]
        
        for path, expected in zip(complex_paths, expected_results):
            with self.subTest(path=path):
                result = self.detector.detect_game_from_path(path)
                self.assertEqual(result, expected)
    
    def test_detect_path_no_match(self):
        """Test path detection returns None for unknown games"""
        test_paths = [
            "/roms/Super Mario World.smc",
            "/games/unknown_game.gba",
            "/path/to/not_pokemon.rom",
            ""
        ]
        
        for path in test_paths:
            with self.subTest(path=path):
                result = self.detector.detect_game_from_path(path)
                self.assertIsNone(result)
    
    def test_detect_path_none_input(self):
        """Test path detection handles None input gracefully"""
        result = self.detector.detect_game_from_path(None)
        self.assertIsNone(result)


class GameDetectorManualOverrideTest(TestCase):
    """Test manual override functionality"""
    
    def setUp(self):
        self.detector = GameDetector()
    
    @patch('builtins.print')  # Mock print to avoid console output during tests
    def test_set_manual_override_valid_game(self, mock_print):
        """Test setting manual override with valid game ID"""
        result = self.detector.set_manual_override("pokemon_sapphire")
        
        self.assertTrue(result)
        self.assertEqual(self.detector.manual_override, "pokemon_sapphire")
        mock_print.assert_called_once()
        self.assertIn("Sapphire", mock_print.call_args[0][0])
    
    @patch('builtins.print')
    def test_set_manual_override_invalid_game(self, mock_print):
        """Test setting manual override with invalid game ID"""
        result = self.detector.set_manual_override("invalid_game")
        
        self.assertFalse(result)
        self.assertIsNone(self.detector.manual_override)
        mock_print.assert_not_called()
    
    def test_clear_manual_override(self):
        """Test clearing manual override"""
        # Set an override first
        self.detector.set_manual_override("pokemon_ruby")
        self.assertEqual(self.detector.manual_override, "pokemon_ruby")
        
        # Clear it
        with patch('builtins.print'):  # Mock print to avoid output
            with patch('dashboard.game_detector.Configuration') as mock_config:
                mock_config_instance = MagicMock()
                mock_config_instance.game_override = 'pokemon_ruby'
                mock_config.get_config.return_value = mock_config_instance
                
                self.detector.clear_manual_override()
                
                self.assertIsNone(self.detector.manual_override)
                # Verify database clear was attempted
                mock_config_instance.save.assert_called_once()
                self.assertEqual(mock_config_instance.game_override, '')
                self.assertEqual(mock_config_instance.detection_source, 'auto')


class GameDetectorCurrentGameTest(TestCase):
    """Test get_current_game functionality"""
    
    def setUp(self):
        self.detector = GameDetector()
    
    @patch('builtins.print')  # Mock print to avoid console output
    @patch('dashboard.models.Configuration')
    def test_get_current_game_database_override(self, mock_config, mock_print):
        """Test get_current_game returns database override first"""
        mock_config_instance = MagicMock()
        mock_config_instance.game_override = 'pokemon_emerald'
        mock_config.get_config.return_value = mock_config_instance
        
        game_id, source = self.detector.get_current_game()
        
        self.assertEqual(game_id, 'pokemon_emerald')
        self.assertEqual(source, 'manual')
        self.assertEqual(self.detector.manual_override, 'pokemon_emerald')
    
    @patch('builtins.print')
    def test_get_current_game_memory_override(self, mock_print):
        """Test get_current_game uses in-memory override"""
        self.detector.manual_override = 'pokemon_ruby'
        
        game_id, source = self.detector.get_current_game()
        
        self.assertEqual(game_id, 'pokemon_ruby')
        self.assertEqual(source, 'manual')
    
    @patch('builtins.print')
    @patch('dashboard.models.Configuration')
    def test_get_current_game_rom_name_detection(self, mock_config, mock_print):
        """Test get_current_game uses ROM name detection"""
        mock_config_instance = MagicMock()
        mock_config_instance.game_override = ''  # No database override
        mock_config.get_config.return_value = mock_config_instance
        
        game_id, source = self.detector.get_current_game(rom_name="Pokemon Sapphire")
        
        self.assertEqual(game_id, 'pokemon_sapphire')
        self.assertEqual(source, 'rom_name')
    
    @patch('builtins.print')
    @patch('dashboard.models.Configuration')
    def test_get_current_game_rom_path_detection(self, mock_config, mock_print):
        """Test get_current_game uses ROM path detection"""
        mock_config_instance = MagicMock()
        mock_config_instance.game_override = ''
        mock_config.get_config.return_value = mock_config_instance
        
        game_id, source = self.detector.get_current_game(
            rom_path="/roms/Pokemon Ruby.gba"
        )
        
        self.assertEqual(game_id, 'pokemon_ruby')
        self.assertEqual(source, 'rom_path')
    
    @patch('builtins.print')
    @patch('dashboard.models.Configuration')
    def test_get_current_game_default_fallback(self, mock_config, mock_print):
        """Test get_current_game returns default when no detection works"""
        mock_config_instance = MagicMock()
        mock_config_instance.game_override = ''
        mock_config.get_config.return_value = mock_config_instance
        
        game_id, source = self.detector.get_current_game(
            rom_name="Unknown Game", 
            rom_path="/roms/unknown.gba"
        )
        
        self.assertEqual(game_id, 'pokemon_red')
        self.assertEqual(source, 'default')
    
    @patch('builtins.print')
    @patch('dashboard.game_detector.Configuration', side_effect=Exception("Database error"))
    def test_get_current_game_database_error_handling(self, mock_config, mock_print):
        """Test get_current_game handles database errors gracefully"""
        game_id, source = self.detector.get_current_game(rom_name="Pokemon Emerald")
        
        # Should fall back to ROM name detection despite database error
        self.assertEqual(game_id, 'pokemon_emerald')
        self.assertEqual(source, 'rom_name')


class GameDetectorUtilityMethodsTest(TestCase):
    """Test utility methods"""
    
    def setUp(self):
        self.detector = GameDetector()
    
    def test_get_game_config_valid(self):
        """Test getting valid game configuration"""
        config = self.detector.get_game_config("pokemon_sapphire")
        
        self.assertIsNotNone(config)
        self.assertIsInstance(config, GameConfig)
        self.assertEqual(config.id, "pokemon_sapphire")
    
    def test_get_game_config_invalid(self):
        """Test getting invalid game configuration returns None"""
        config = self.detector.get_game_config("invalid_game")
        self.assertIsNone(config)
    
    def test_get_all_games(self):
        """Test getting all games list for UI"""
        games_list = self.detector.get_all_games()
        
        self.assertIsInstance(games_list, list)
        self.assertGreater(len(games_list), 0)
        
        # Test structure of returned games
        for game in games_list:
            self.assertIn("id", game)
            self.assertIn("name", game)
            self.assertIn("platform", game)
            self.assertIsInstance(game["id"], str)
            self.assertIsInstance(game["name"], str)
            self.assertIsInstance(game["platform"], str)
        
        # Test that expected games are present
        game_ids = [game["id"] for game in games_list]
        expected_ids = [
            "pokemon_red", "pokemon_sapphire", "pokemon_ruby",
            "pokemon_emerald", "pokemon_firered", "pokemon_leafgreen"
        ]
        
        for expected_id in expected_ids:
            self.assertIn(expected_id, game_ids)


class GameDetectorLuaFormattingTest(TestCase):
    """Test Lua configuration formatting"""
    
    def setUp(self):
        self.detector = GameDetector()
    
    def test_format_game_config_for_lua_simple(self):
        """Test Lua formatting for simple static game (Pokemon Red)"""
        lua_config = self.detector.format_game_config_for_lua("pokemon_red")
        
        self.assertIsNotNone(lua_config)
        self.assertIn('id="pokemon_red"', lua_config)
        self.assertIn('name="Pokémon Red/Blue"', lua_config)
        self.assertIn('platform="Game Boy"', lua_config)
        self.assertIn('memoryType="static"', lua_config)
        
        # Test memory addresses are formatted correctly
        self.assertIn('playerDirection=0x0000C109', lua_config)
        self.assertIn('playerX=0x0000D362', lua_config)
        self.assertIn('playerY=0x0000D361', lua_config)
        self.assertIn('mapId=0x0000D35E', lua_config)
        
        # Test direction encoding
        self.assertIn('[0]="DOWN"', lua_config)
        self.assertIn('[4]="UP"', lua_config)
        self.assertIn('[8]="LEFT"', lua_config)
        self.assertIn('[12]="RIGHT"', lua_config)
        
        # Should have fallbackAddresses=nil for static games
        self.assertIn('fallbackAddresses=nil', lua_config)
    
    def test_format_game_config_for_lua_dynamic(self):
        """Test Lua formatting for dynamic game with fallbacks (Pokemon Sapphire)"""
        lua_config = self.detector.format_game_config_for_lua("pokemon_sapphire")
        
        self.assertIsNotNone(lua_config)
        self.assertIn('id="pokemon_sapphire"', lua_config)
        self.assertIn('memoryType="dynamic"', lua_config)
        
        # Test that nil addresses are formatted correctly
        self.assertIn('playerDirection=nil', lua_config)
        self.assertIn('playerX=nil', lua_config)
        self.assertIn('playerY=nil', lua_config)
        self.assertIn('mapId=nil', lua_config)
        
        # Test direction encoding includes both standard and TBL
        self.assertIn('[1]="DOWN"', lua_config)
        self.assertIn('[121]="UP"', lua_config)  # 0x79 = 121
        
        # Test fallback addresses are included
        self.assertNotIn('fallbackAddresses=nil', lua_config)
        self.assertIn('fallbackAddresses={', lua_config)
        self.assertIn('playerX=0x02025734', lua_config)  # First fallback address
    
    def test_format_game_config_for_lua_invalid(self):
        """Test Lua formatting returns None for invalid game"""
        lua_config = self.detector.format_game_config_for_lua("invalid_game")
        self.assertIsNone(lua_config)
    
    def test_lua_config_is_valid_lua_syntax(self):
        """Test that generated Lua config has valid syntax structure"""
        lua_config = self.detector.format_game_config_for_lua("pokemon_red")
        
        # Basic syntax checks
        self.assertTrue(lua_config.startswith('{'))
        self.assertTrue(lua_config.endswith('}'))
        
        # Check for balanced braces
        open_braces = lua_config.count('{')
        close_braces = lua_config.count('}')
        self.assertEqual(open_braces, close_braces)
        
        # Check for proper key=value formatting
        self.assertIn('=', lua_config)
        self.assertNotIn('==', lua_config)  # No double equals
        
        # Check hex formatting
        hex_addresses = re.findall(r'0x[0-9A-F]{8}', lua_config)
        self.assertGreater(len(hex_addresses), 0)
        
        # All hex addresses should be 8 digits (with 0x prefix)
        for hex_addr in hex_addresses:
            self.assertEqual(len(hex_addr), 10)  # 0x + 8 digits


class GetGameDetectorTest(TestCase):
    """Test global detector instance functionality"""
    
    def test_get_game_detector_singleton(self):
        """Test get_game_detector returns same instance (singleton pattern)"""
        detector1 = get_game_detector()
        detector2 = get_game_detector()
        
        self.assertIs(detector1, detector2)
        self.assertIsInstance(detector1, GameDetector)
    
    def test_get_game_detector_properly_initialized(self):
        """Test global detector instance is properly initialized"""
        detector = get_game_detector()
        
        self.assertIsInstance(detector.games, dict)
        self.assertGreater(len(detector.games), 0)
        self.assertIsNone(detector.manual_override)
    
    def test_multiple_calls_preserve_state(self):
        """Test multiple calls preserve detector state"""
        detector1 = get_game_detector()
        detector1.set_manual_override("pokemon_emerald")
        
        detector2 = get_game_detector()
        self.assertEqual(detector2.manual_override, "pokemon_emerald")