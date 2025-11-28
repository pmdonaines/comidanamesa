#!/bin/bash

uv run python manage.py runserver &
npm run watch:css &
wait