from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.dataloader import DataError      # noqa: E402
from core.game import GameSession          # noqa: E402

CLASS_MODE_YEARS = 5

DEFAULT_MAX_FRAMES = 60000


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python src/main.py",
        description="Secure Company Simulator ― 情報を守る担当になって会社を続けるゲーム",
    )
    parser.add_argument("--skip-school", action="store_true",
                        help="学校編を飛ばして会社編から始める")
    parser.add_argument("--class-mode", action="store_true",
                        help=f"授業モード（会社編 {CLASS_MODE_YEARS} 年）")
    parser.add_argument("--seed", type=int, default=None,
                        help="乱数のたねを固定して起動する（同じ展開を再現できる）")
    parser.add_argument("--auto-play", action="store_true",
                        help="自動プレイで通し動作を確認する")
    parser.add_argument("--max-frames", type=int, default=DEFAULT_MAX_FRAMES,
                        help="自動プレイを打ち切るフレーム数")
    parser.add_argument("--debug", action="store_true",
                        help="デバッグ情報を標準エラーに出す")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.auto_play and not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    total_years = CLASS_MODE_YEARS if args.class_mode else None

    try:
        session = GameSession(
            seed=args.seed,
            total_years=total_years,
            school=not args.skip_school,
        )
    except DataError as error:
        return _report_data_error(error)

    from ui.app import App

    app = App(
        session=session,
        auto_play=args.auto_play,
        seed=args.seed,
        total_years=total_years,
        class_mode=args.class_mode,
        max_frames=args.max_frames,
        skip_school=args.skip_school,
    )

    exit_code = app.run()

    if args.auto_play:
        return _report_auto_play(app, args)

    return exit_code


def _report_auto_play(app, args) -> int:
    if not app.reached_result:
        print(
            f"[auto-play] 最終結果画面に到達できませんでした"
            f"（seed={args.seed} / {app.frames} フレームで打ち切り）",
            file=sys.stderr,
        )
        return 1

    score = app.session.final_score()
    achieved = sum(1 for ok in score.clear_flags.values() if ok)
    print(
        f"[auto-play] seed={app.session.seed} "
        f"総合点 {score.total} / 1000  評価 {score.rank}  "
        f"クリア条件 {achieved}/5  "
        f"{'倒産' if score.bankrupt else f'{len(app.session.logs)} 年経営'}  "
        f"({app.frames} フレーム)"
    )
    return 0


def _report_data_error(error: DataError) -> int:
    print("データファイルに問題があります", file=sys.stderr)
    print(str(error), file=sys.stderr)
    print("data フォルダの JSON を直してから、もう一度起動してください。", file=sys.stderr)

    try:
        _show_data_error_window(error)
    except Exception:
        pass

    return 2


def _show_data_error_window(error: DataError) -> None:
    import pygame

    from ui import fonts, theme, widgets

    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode((theme.SCREEN_W, theme.SCREEN_H))
    pygame.display.set_caption("Secure Company Simulator ― データの問題")

    close_button = widgets.Button(
        rect=pygame.Rect(1000, 560, 220, theme.BUTTON_H),
        label="終わる",
        kind="primary",
    )

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if close_button.hit(event.pos):
                    running = False

        screen.fill(theme.BG)
        panel = pygame.Rect(140, 160, 1000, 400)
        widgets.draw_panel(screen, panel, theme.CARD, border=theme.RED, border_width=2)

        widgets.draw_text(screen, "データファイルに問題があります", (panel.x + 40, panel.y + 36),
                          theme.SIZE_TITLE, theme.RED, bold=True)
        widgets.draw_wrapped(screen, str(error), (panel.x + 40, panel.y + 110),
                             panel.width - 80, theme.SIZE_BODY, theme.INK,
                             max_lines=4, leading=8)
        widgets.draw_wrapped(
            screen,
            "data フォルダの JSON を直してから、もう一度起動してください。",
            (panel.x + 40, panel.y + 250), panel.width - 80,
            theme.SIZE_BODY, theme.GREY, max_lines=2, leading=8,
        )

        widgets.draw_button(screen, close_button)
        pygame.display.flip()

    pygame.display.quit()


if __name__ == "__main__":
    sys.exit(main())
