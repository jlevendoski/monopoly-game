#!/bin/bash

# Use $PYTHON explicitly
PYTHON=python3
#
# Monopoly Test Suite Runner
#
# Runs all tests in sequence and reports results.
#
# Usage:
#   ./run_all_tests.sh           # Run all tests
#   ./run_all_tests.sh unit      # Run only unit tests
#   ./run_all_tests.sh integration  # Run only integration tests
#   ./run_all_tests.sh e2e       # Run only E2E tests
#   ./run_all_tests.sh gui       # Run only GUI tests (requires display)
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Change to project root
cd "$(dirname "$0")"

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                 MONOPOLY COMPLETE TEST SUITE                         ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Track results
TOTAL_PASSED=0
TOTAL_FAILED=0
RESULTS=""

run_test() {
    local name="$1"
    local cmd="$2"
    
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE} Running: $name${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    if eval "$cmd"; then
        echo -e "  ${GREEN}✓ $name: PASSED${NC}"
        RESULTS="$RESULTS\n  ${GREEN}✓ $name: PASSED${NC}"
        ((TOTAL_PASSED++)) || true
    else
        echo -e "  ${RED}✗ $name: FAILED${NC}"
        RESULTS="$RESULTS\n  ${RED}✗ $name: FAILED${NC}"
        ((TOTAL_FAILED++)) || true
    fi
}

# Determine which tests to run
TEST_TYPE="${1:-all}"

case "$TEST_TYPE" in
    unit)
        echo -e "${YELLOW}Running unit tests only...${NC}"
        run_test "Game Engine Tests" "$PYTHON tests/test_game_engine/test_game_engine.py"
        run_test "Network Tests" "$PYTHON tests/test_network/test_network.py"
        run_test "Persistence Tests" "$PYTHON tests/test_persistence/test_persistence.py"
        ;;
    
    integration)
        echo -e "${YELLOW}Running integration tests only...${NC}"
        run_test "Two-Player Integration" "$PYTHON tests/test_integration/test_two_player_integration.py"
        run_test "Reconnection Tests" "$PYTHON tests/test_integration/test_reconnection.py"
        ;;
    
    e2e)
        echo -e "${YELLOW}Running end-to-end tests only...${NC}"
        run_test "Full Game E2E" "$PYTHON tests/test_e2e/test_full_game_e2e.py"
        ;;
    
    gui)
        echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BOLD}${CYAN}║                    GUI TESTING INSTRUCTIONS                          ║${NC}"
        echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${YELLOW}Prerequisites: External server must be running${NC}"
        echo ""
        echo -e "${CYAN}══════════════════════════════════════════════════════════════════════${NC}"
        echo -e "${BOLD}OPTION 1: Automated Test Against Server${NC}"
        echo -e "${CYAN}══════════════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  ${BOLD}Full GUI test (launches two client windows):${NC}"
        echo -e "     $PYTHON tests/test_gui_dual/test_gui_against_server.py --server YOUR_SERVER_ADDRESS"
        echo ""
        echo -e "  ${BOLD}Protocol-only test (no GUI, just verifies connection):${NC}"
        echo -e "     $PYTHON tests/test_gui_dual/test_gui_against_server.py --server YOUR_SERVER_ADDRESS --protocol-only"
        echo ""
        echo -e "  ${BOLD}With custom port:${NC}"
        echo -e "     $PYTHON tests/test_gui_dual/test_gui_against_server.py --server YOUR_SERVER_ADDRESS --port 9000"
        echo ""
        echo -e "${CYAN}══════════════════════════════════════════════════════════════════════${NC}"
        echo -e "${BOLD}OPTION 2: Manual Two-Client Test${NC}"
        echo -e "${CYAN}══════════════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  ${BOLD}Set server address, then launch clients:${NC}"
        echo -e "     export MONOPOLY_SERVER_HOST=YOUR_SERVER_ADDRESS"
        echo -e "     export MONOPOLY_SERVER_PORT=8765"
        echo -e "     $PYTHON -m client.main  # Terminal 1"
        echo -e "     $PYTHON -m client.main  # Terminal 2"
        echo ""
        echo -e "  ${BOLD}Test Flow:${NC}"
        echo -e "     1. Client 1: Enter name, Connect, Create Game"
        echo -e "     2. Client 2: Enter name, Connect, Join Game"
        echo -e "     3. Client 1: Start Game"
        echo -e "     4. Both: Take turns, verify state sync"
        echo ""
        echo -e "${CYAN}══════════════════════════════════════════════════════════════════════${NC}"
        echo -e "${BOLD}OPTION 3: Local GUI Test (no server, tests UI components only)${NC}"
        echo -e "${CYAN}══════════════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "     $PYTHON -m tests.test_gui.test_gui"
        echo ""
        ;;
    
    all)
        echo -e "${YELLOW}Running complete test suite...${NC}"
        
        # Unit tests
        echo ""
        echo -e "${CYAN}=== UNIT TESTS ===${NC}"
        run_test "Game Engine Tests" "$PYTHON tests/test_game_engine/test_game_engine.py"
        run_test "Network Tests" "$PYTHON tests/test_network/test_network.py"
        
        # Integration tests
        echo ""
        echo -e "${CYAN}=== INTEGRATION TESTS ===${NC}"
        run_test "Two-Player Integration" "$PYTHON tests/test_integration/test_two_player_integration.py"
        run_test "Reconnection Tests" "$PYTHON tests/test_integration/test_reconnection.py"
        
        # E2E tests
        echo ""
        echo -e "${CYAN}=== END-TO-END TESTS ===${NC}"
        run_test "Full Game E2E" "$PYTHON tests/test_e2e/test_full_game_e2e.py"
        
        echo ""
        echo -e "${YELLOW}Note: GUI tests require manual execution. See: ./run_all_tests.sh gui${NC}"
        ;;
    
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Usage: $0 [unit|integration|e2e|gui|all]"
        exit 1
        ;;
esac

# Summary
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                         TEST SUMMARY                                 ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "$RESULTS"
echo ""
echo -e "  ${BOLD}Total Passed: ${GREEN}$TOTAL_PASSED${NC}"
echo -e "  ${BOLD}Total Failed: ${RED}$TOTAL_FAILED${NC}"
echo ""

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${BOLD}${GREEN}══════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}                      ALL TESTS PASSED! ✓                             ${NC}"
    echo -e "${BOLD}${GREEN}══════════════════════════════════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${BOLD}${RED}══════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${RED}                      SOME TESTS FAILED ✗                             ${NC}"
    echo -e "${BOLD}${RED}══════════════════════════════════════════════════════════════════════${NC}"
    exit 1
fi
