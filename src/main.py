import streamlit as st

import house_questions
import solar_questions
import savings_outputs

from streamlit_wizard import Wizard, Page

st.set_page_config(initial_sidebar_state="collapsed")


class YourHousePage(Page):
    def render(self) -> dict:
        return dict(house=house_questions.render())


class SolarPage(Page):
    def render(self) -> dict:
        return dict(solar=solar_questions.render())


class ResultsPage(Page):
    def render(self):
        house = st.session_state["page_state"]["house"]["house"]
        solar = st.session_state["page_state"]["solar"]["solar"]
        savings_outputs.render(house=house, solar=solar)


wizard = Wizard(pages=[YourHousePage("house"), SolarPage("solar"), ResultsPage("results")])

st.markdown(
    "<p class='title'>Cut your bills with solar + heat pump </p>"
    "<p class='description'> How much money and carbon can you save by installing a heat pump "
    "or solar panels? Get an estimate in 5 minutes!</p>",
    unsafe_allow_html=True,
)

wizard.render()
