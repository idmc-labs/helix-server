from utils.tests import HelixTestCase
from utils.common import add_clone_prefix


class TestClonedPrefix(HelixTestCase):
    def setUp(self) -> None:
        self.sentence = "Test sentence"
        self.sentence_2 = "Test sentence Clone:"

    def test_should_add_cloned_prifix_at_first_time_cloned(self):
        self.assertEqual(f"Clone: {self.sentence}", add_clone_prefix(self.sentence))

    def test_should_increment_digit_if_cloned_mutiple_times(self):
        second_cloned_sentence = add_clone_prefix(self.sentence)
        self.assertEqual(f"Clone 2: {self.sentence}", add_clone_prefix(second_cloned_sentence))

        third_cloned_sentence = add_clone_prefix(second_cloned_sentence)
        self.assertEqual(f"Clone 3: {self.sentence}", add_clone_prefix(third_cloned_sentence))

        forth_cloned_sentense = add_clone_prefix(third_cloned_sentence)
        self.assertEqual(f"Clone 4: {self.sentence}", add_clone_prefix(forth_cloned_sentense))

    def test_should_increment_only_initial_prefix_if_duplicated(self):
        second_cloned_sentence = add_clone_prefix(self.sentence_2)
        self.assertEqual(f"Clone 2: {self.sentence_2}", add_clone_prefix(second_cloned_sentence))

        third_cloned_sentence = add_clone_prefix(second_cloned_sentence)
        self.assertEqual(f"Clone 3: {self.sentence_2}", add_clone_prefix(third_cloned_sentence))

        forth_cloned_sentense = add_clone_prefix(third_cloned_sentence)
        self.assertEqual(f"Clone 4: {self.sentence_2}", add_clone_prefix(forth_cloned_sentense))
