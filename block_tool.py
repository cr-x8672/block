import configparser
import enum
import itertools
from requests_oauthlib import OAuth1
import requests
import urllib
import sys


class RequestsMethod(enum.Enum):
    POST = enum.auto()
    GET = enum.auto()


class BlockTool(object):
    """単語単位でユーザーをブロック

    Attributes:
        _target_word: (str): ブロック対象となる単語
        _maximum_count: (int): 一回あたりの検索数(最大100)
        _search_limit: (int): 検索回数の上限値(最大180/15分でリセット)
        _target_parse: (str): ブロック設定を含むパース情報
        _auth: (str): API認証情報
    """

    def __init__(self, target_word, maximum_count=100, search_limit=180):
        """
        Args:
            target_word: (str): ブロック対象となる単語
            maximum_count: (int): 一回あたりの検索数(最大100)
            search_limit: (int): 検索回数の上限値(最大180/15分でリセット)
        """
        self._target_word = target_word
        self._maximum_count = maximum_count
        self._search_limit = search_limit
        self._target_parse = None
        self._auth = None

    def main(self):
        # API認証情報設定
        self.set_auth()
        # URLパース設定
        self.set_url_parse()
        # ブロック処理実行
        self.exec_block_process()

    def set_auth(self):
        """API認証情報設定"""
        # 認証設定ファイル読み込み
        config = configparser.ConfigParser()
        config.read('./config.ini', encoding='utf-8')

        # 認証情報取得
        consumer_key = config['Consumer']['API key']
        consumer_secret_key = config['Consumer']['API secret key']
        access_token = config['Token']['Access token']
        access_token_secret = config['Token']['Access token secret']

        # API認証情報セット
        self._auth = OAuth1(consumer_key, consumer_secret_key, access_token, access_token_secret)

    def set_url_parse(self):
        """URLパース設定"""
        # RTは除く設定、ハッシュタグのみ指定
        target = f'#{self._target_word} exclude:retweets'
        # パース済み情報セット
        self._target_parse = urllib.parse.quote_plus(target)

    def exec_block_process(self):
        """ブロック処理実行"""
        try:
            current_id = 0
            for i in itertools.count():
                username_list = []
                # 検索回数の上限に達した場合
                if i > self._search_limit:
                    print(f'検索回数の上限値({self._search_limit}回)に達しました。')
                    break

                # ユーザー情報取得処理実行
                users_info = self._search_tweets(current_id)
                # 取得可能なデータが無い場合
                if not users_info:
                    print('取得可能なデータがありません。')
                    break

                # 対象のユーザー名 ・検索済みツイート位置の取得
                for user in users_info:
                    username = user['user']['screen_name']
                    username_list.append(username)
                    current_id = int(user["id"]) - 1

                # ブロック処理実行
                self._block_users(username_list)

        except Exception as e:
            print(f'予期せぬエラーが発生しました。（{str(e)}）')

    def _search_tweets(self, current_id):
        """ユーザー情報取得処理実行
        対象の単語を含むツイートを行っているユーザー情報を
        指定の件数（maximum_count）取得する。

        Args:
            current_id: (str): 検索済みのツイート位置

        Returns:
            users_info: (list): 対象のユーザー情報
        """
        # ユーザー情報取得API
        url = f'https://api.twitter.com/1.1/search/tweets.json?q={self._target_parse}' \
              f'&count={self._maximum_count}&max_id={str(current_id)}'
        response = self._get_response(url=url, method=RequestsMethod.GET.name)
        users_info = response.json()['statuses']

        return users_info

    def _block_users(self, username_list):
        """ブロック処理実行
        対象のユーザーを一件ずつブロック処理実行。

        Args:
            username_list: (list): 対象のユーザー名リスト
        """
        for screen_name in username_list:
            # ブロック実行API
            url = f'https://api.twitter.com/1.1/blocks/create.json?skip_status=1&include_entities=false&' \
                  f'screen_name={screen_name}'
            self._get_response(url=url, method=RequestsMethod.POST.name)
            print(f'@{screen_name}さんをブロックしました。')

    def _get_response(self, url, method):
        """リクエスト実行

        Args:
            url: (str): URL
            method: (str): リクエストメソッド

        Returns:
            response: (obj): リクエスト結果
        """
        response = requests.request(method=method, url=url, auth=self._auth)

        return response


if __name__ == '__main__':
    bt = BlockTool(target_word=sys.argv[1])
    bt.main()
