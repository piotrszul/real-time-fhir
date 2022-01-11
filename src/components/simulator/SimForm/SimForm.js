import React from "react";
import { CardContent } from "@mui/material";
import { RegularCard } from "../../ComponentStyles";
import SimulationFormInput from "./SimFormInput";
import SimulationFormButtons from "./SimFormButtons";

const SimulationForm = (props) => (
  <RegularCard sx={{ my: 2.5 }}>
    <CardContent>
      <SimulationFormInput formState={props.formState} setForm={props.setForm} />
      <SimulationFormButtons
        defaultAttributes={props.defaultAttributes}
        setAttributes={props.setAttributes}
        formState={props.formState}
        setTable={props.setTable}
        statusState={props.statusState}
        statusDispatch={props.statusDispatch}
      />
    </CardContent>
  </RegularCard>
);

export default React.memo(SimulationForm);
