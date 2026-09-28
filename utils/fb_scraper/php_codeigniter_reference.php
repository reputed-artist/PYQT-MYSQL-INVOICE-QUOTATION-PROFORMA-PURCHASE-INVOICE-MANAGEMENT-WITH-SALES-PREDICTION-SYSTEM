<?php
// Facebook Comments GraphQL — PHP (CodeIgniter 4) reference port.
// Mirrors comment_scraper.py. Doc IDs rotate — update when FB changes them.
// Comments: 27806180149070312 | Replies: 26570577339199586

function fb_feedback_id(string $post_id): string
{
    return base64_encode("feedback:{$post_id}");
}

function fb_comments_variables(string $feedback_id, ?string $cursor = null): array
{
    return [
        'commentsAfterCount'   => -1,
        'commentsAfterCursor'  => $cursor,
        'commentsBeforeCount'  => null,
        'commentsBeforeCursor' => null,
        'commentsIntentToken'  => null,
        'feedLocation'         => 'POST_PERMALINK_DIALOG',
        'focusCommentID'       => null,
        'scale'                => 2,
        'useDefaultActor'      => false,
        'id'                   => $feedback_id,
        '__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider' => 'AUTO_TRANSLATE',
        '__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider' => false,
        '__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider' => true,
        '__relay_internal__pv__IsWorkUserrelayprovider' => false,
    ];
}


function fb_replies_variables(string $comment_feedback_id, string $expansion_token): array
{
    return [
        'clientKey' => null,
        'expansionToken' => $expansion_token,
        'feedLocation' => 'POST_PERMALINK_DIALOG',
        'focusCommentID' => null,
        'scale' => 2,
        'useDefaultActor' => false,
        'id' => $comment_feedback_id,
        '__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider' => 'AUTO_TRANSLATE',
        '__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider' => false,
        '__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider' => true,
        '__relay_internal__pv__IsWorkUserrelayprovider' => false,
    ];
}

function fb_graphql_post(array $variables, string $doc_id, string $friendly, string $cookies, string $dtsg = '', ?string $proxy = null): array
{
    $user_id = '0';
    if (preg_match('/c_user=(\d+)/', $cookies, $m)) {
        $user_id = $m[1];
    }
    $fields = [
        'av' => $user_id,
        '__user' => $user_id,
        '__a' => '1',
        'fb_dtsg' => $dtsg,
        'fb_api_caller_class' => 'RelayModern',
        'server_timestamps' => 'true',
        'doc_id' => $doc_id,
        'variables' => json_encode($variables, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE),
    ];
    $body = http_build_query($fields);
    $ch = curl_init('https://www.facebook.com/api/graphql/');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $body,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_ENCODING => '',
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/x-www-form-urlencoded',
            'User-Agent: Mozilla/5.0',
            'Origin: https://www.facebook.com',
            'Referer: https://www.facebook.com/',
            'X-FB-Friendly-Name: ' . $friendly,
            'Cookie: ' . $cookies,
        ],
    ]);
    if ($proxy) {
        curl_setopt($ch, CURLOPT_PROXY, $proxy);
    }
    $raw = curl_exec($ch);
    $err = curl_error($ch);
    $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($raw === false || $raw === '') {
        throw new \RuntimeException("cURL failed: {$err} (HTTP {$code})");
    }
    return [$code, $raw];
}

function fb_parse_first_json(string $raw): array
{
    $text = trim($raw);
    if (str_starts_with($text, 'for (;;);')) {
        $text = trim(substr($text, strlen('for (;;);')));
    }
    $first = trim(strtok($text, "\n"));
    $data = json_decode($first, true);
    if (!is_array($data)) {
        throw new \RuntimeException('Bad GraphQL JSON: ' . substr($first, 0, 300));
    }
    if (isset($data['errors'])) {
        throw new \RuntimeException('GraphQL error: ' . json_encode($data['errors'], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
    }
    return $data;
}

function fb_fetch_comments_page(string $post_id, string $cookies, string $dtsg = '', ?string $cursor = null): array
{
    $vars = fb_comments_variables(fb_feedback_id($post_id), $cursor);
    // log_message('debug', 'FB vars: ' . json_encode($vars));
    [$code, $raw] = fb_graphql_post($vars, '27806180149070312', 'CommentsListComponentsPaginationQuery', $cookies, $dtsg);
    if ($code !== 200) {
        throw new \RuntimeException("Facebook HTTP {$code}: " . substr($raw, 0, 500));
    }
    $j = fb_parse_first_json($raw);
    $block = $j['data']['node']['comment_rendering_instance_for_feed_location']['comments'] ?? [];
    return [$block['edges'] ?? [], $block['page_info']['end_cursor'] ?? null, $j];
}
